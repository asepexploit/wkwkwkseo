"""Launch 1 Chrome dengan CDP, anti-detection (persis pola mr4sepgood)."""
from __future__ import annotations

import json
import shutil
import socket
import subprocess
import tempfile
import time
import urllib.request
from contextlib import suppress
from pathlib import Path

from websocket import WebSocketException, create_connection  # type: ignore[import-untyped]

_CHROME_CANDIDATES = (
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
)


def find_chrome() -> str | None:
    for name in ("chrome", "google-chrome", "chromium", "chromium-browser"):
        found = shutil.which(name)
        if found:
            return found
    for path in _CHROME_CANDIDATES:
        if Path(path).exists():
            return path
    return None


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class CDPDriver:
    """CDP driver murni via websocket — tanpa Playwright overhead."""

    def __init__(self, host: str, port: int, timeout_s: float = 15.0) -> None:
        self._base = f"http://{host}:{port}"
        self._ws = None
        self._msg_id = 0
        self._connect(timeout_s)

    def _connect(self, timeout_s: float) -> None:
        deadline = time.monotonic() + timeout_s
        ws_url = None
        while time.monotonic() < deadline:
            try:
                ws_url = self._first_page_ws()
                if ws_url:
                    break
            except Exception:
                pass
            time.sleep(0.3)
        if not ws_url:
            raise RuntimeError("Gagal connect ke Chrome CDP (timeout)")
        self._ws = create_connection(ws_url, timeout=60)
        self._send("Page.enable")
        # Anti-detection: Runtime.enable lalu langsung disable
        self._send("Runtime.enable")
        self._send("Runtime.disable")
        with suppress(Exception):
            self._send("Target.setDiscoverTargets", {"discover": True})
        with suppress(Exception):
            self._send("Target.setAutoAttach", {
                "autoAttach": True,
                "waitForDebuggerOnStart": False,
                "flatten": True,
            })

    def _first_page_ws(self) -> str | None:
        with urllib.request.urlopen(f"{self._base}/json/list", timeout=3) as resp:
            targets = json.loads(resp.read().decode())
        for t in targets:
            if t.get("type") == "page" and t.get("webSocketDebuggerUrl"):
                return t["webSocketDebuggerUrl"]
        req = urllib.request.Request(f"{self._base}/json/new?about:blank", method="PUT")
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode())
            return data.get("webSocketDebuggerUrl")

    def _send(self, method: str, params: dict | None = None, session_id: str | None = None) -> dict:
        if self._ws is None:
            raise RuntimeError("CDP tertutup")
        self._msg_id += 1
        my_id = self._msg_id
        payload: dict = {"id": my_id, "method": method, "params": params or {}}
        if session_id is not None:
            payload["sessionId"] = session_id
        self._ws.send(json.dumps(payload))
        while True:
            raw = self._ws.recv()
            msg = json.loads(raw)
            if msg.get("method") == "Page.javascriptDialogOpening":
                with suppress(Exception):
                    self._ws.send(json.dumps({
                        "id": 0,
                        "method": "Page.handleJavaScriptDialog",
                        "params": {"accept": True},
                    }))
                continue
            if msg.get("id") == my_id and msg.get("sessionId") == session_id:
                if "error" in msg:
                    raise RuntimeError(f"CDP {method}: {msg['error']}")
                return msg.get("result", {})

    def evaluate(self, expression: str, session_id: str | None = None):
        result = self._send(
            "Runtime.evaluate",
            {"expression": expression, "returnByValue": True, "awaitPromise": True},
            session_id=session_id,
        )
        return result.get("result", {}).get("value")

    def goto(self, url: str, timeout_ms: int = 30000) -> None:
        self._send("Page.navigate", {"url": url})
        deadline = time.monotonic() + timeout_ms / 1000
        while time.monotonic() < deadline:
            state = self.evaluate("try{document.readyState}catch(e){''}")
            if state in ("interactive", "complete"):
                time.sleep(1.0)
                return
            time.sleep(0.2)
        raise RuntimeError(f"Timeout memuat {url}")

    def set_cookies(self, cookies: list[dict]) -> int:
        with suppress(Exception):
            self._send("Network.enable")
        applied = 0
        for c in cookies:
            if not c.get("name") or not c.get("domain"):
                continue
            try:
                params: dict = {
                    "name": str(c["name"]),
                    "value": str(c.get("value", "")),
                    "domain": str(c["domain"]),
                    "path": str(c.get("path", "/")),
                    "secure": bool(c.get("secure", False)),
                    "httpOnly": bool(c.get("httpOnly", False)),
                }
                # editthiscookie export pakai "expirationDate", CDP terima "expires"
                exp = c.get("expirationDate") or c.get("expires")
                if isinstance(exp, (int, float)):
                    params["expires"] = float(exp)
                same_site_raw = str(c.get("sameSite") or "").lower()
                same_site_map = {"lax": "Lax", "strict": "Strict", "no_restriction": "None"}
                if same_site_raw in same_site_map:
                    params["sameSite"] = same_site_map[same_site_raw]
                self._send("Network.setCookie", params)
                applied += 1
            except Exception:
                pass
        return applied

    def open_new_tab(self, url: str = "about:blank", new_window: bool = False) -> str:
        """Buka tab/window baru via CDP Target.createTarget, return target id."""
        try:
            result = self._send("Target.createTarget", {
                "url": url,
                "newWindow": new_window,
            })
            return result.get("targetId", "")
        except Exception:
            # fallback ke HTTP API
            req = urllib.request.Request(f"{self._base}/json/new?{url}", method="PUT")
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())
                return data.get("id", "")

    def connect_tab(self, tab_id: str) -> "CDPDriver":
        """Return CDPDriver baru yang terkoneksi ke tab berbeda via websocket sendiri.
        Tab ini berjalan independen — aman dipakai dari thread terpisah."""
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            try:
                with urllib.request.urlopen(f"{self._base}/json/list", timeout=3) as resp:
                    targets = json.loads(resp.read().decode())
                for t in targets:
                    if t.get("id") == tab_id and t.get("webSocketDebuggerUrl"):
                        inst = object.__new__(CDPDriver)
                        inst._base = self._base
                        inst._msg_id = 0
                        inst._ws = create_connection(t["webSocketDebuggerUrl"], timeout=60)
                        inst._send("Page.enable")
                        inst._send("Runtime.enable")
                        inst._send("Runtime.disable")
                        return inst
            except Exception:
                pass
            time.sleep(0.3)
        raise RuntimeError(f"Gagal connect ke tab {tab_id}")

    def attach_tab(self, tab_id: str) -> bool:
        """Switch CDP ke tab lain berdasarkan id."""
        try:
            with urllib.request.urlopen(f"{self._base}/json/list", timeout=3) as resp:
                targets = json.loads(resp.read().decode())
        except Exception:
            return False
        for t in targets:
            if t.get("id") == tab_id and t.get("type") == "page":
                ws_url = t.get("webSocketDebuggerUrl")
                if not ws_url:
                    return False
                if self._ws:
                    with suppress(Exception):
                        self._ws.close()
                self._ws = create_connection(ws_url, timeout=60)
                self._send("Page.enable")
                return True
        return False

    def close_tab(self, tab_id: str) -> None:
        with suppress(Exception):
            urllib.request.urlopen(f"{self._base}/json/close/{tab_id}", timeout=3)

    def current_url(self) -> str:
        return self.evaluate("location.href") or ""

    def click_cf_iframe(self) -> bool:
        """Klik checkbox Cloudflare Turnstile di iframe cross-origin via CDP."""
        targets = self._send("Target.getTargets").get("targetInfos", [])
        iframe = next(
            (t for t in targets if t.get("type") == "iframe"
             and "challenges.cloudflare.com" in (t.get("url") or "")),
            None,
        )
        if iframe is None:
            return False
        target_id = iframe["targetId"]
        attach = self._send("Target.attachToTarget", {"targetId": target_id, "flatten": True})
        sid = attach.get("sessionId")
        if not sid:
            return False
        size = self._send(
            "Runtime.evaluate",
            {"expression": "({w:window.innerWidth,h:window.innerHeight})", "returnByValue": True},
            session_id=sid,
        ).get("result", {}).get("value") or {}
        h = float(size.get("h") or 66)
        x, y = 30.0, h / 2
        self._send("Input.dispatchMouseEvent", {"type": "mouseMoved", "x": x, "y": y}, session_id=sid)
        time.sleep(0.3)
        self._send("Input.dispatchMouseEvent",
                   {"type": "mousePressed", "x": x, "y": y, "button": "left", "clickCount": 1},
                   session_id=sid)
        time.sleep(0.08)
        self._send("Input.dispatchMouseEvent",
                   {"type": "mouseReleased", "x": x, "y": y, "button": "left", "clickCount": 1},
                   session_id=sid)
        return True

    def screenshot(self) -> bytes | None:
        """Ambil screenshot halaman saat ini, return bytes PNG atau None."""
        try:
            result = self._send("Page.captureScreenshot", {"format": "png", "captureBeyondViewport": False})
            import base64
            data = result.get("data")
            if data:
                return base64.b64decode(data)
        except Exception as e:
            from contextlib import suppress as _suppress
            with _suppress(Exception):
                pass
        return None

    def close(self) -> None:
        if self._ws:
            with suppress(Exception):
                self._ws.close()
            self._ws = None


class ChromeSession:
    """Context manager: 1 Chrome process + CDPDriver."""

    def __init__(self, headless: bool = False) -> None:
        self._headless = headless
        self._proc: subprocess.Popen | None = None
        self._profile_dir: str | None = None
        self.driver: CDPDriver | None = None

    def start(self) -> CDPDriver:
        chrome = find_chrome()
        if not chrome:
            raise RuntimeError("Chrome tidak ditemukan")
        port = _free_port()
        self._profile_dir = tempfile.mkdtemp(prefix="wkwkwk_")
        args = [
            chrome,
            "--incognito",
            f"--remote-debugging-port={port}",
            f"--user-data-dir={self._profile_dir}",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-popup-blocking",
            "--remote-allow-origins=*",
            "--disable-blink-features=AutomationControlled",
            "--ignore-certificate-errors",
            "--allow-insecure-localhost",
            "--disable-features=HttpsUpgrades,HttpsFirstBalancedMode,HttpsFirstModeIncognito",
        ]
        if self._headless:
            args.append("--headless=new")
        self._proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(1.5)
        self.driver = CDPDriver("127.0.0.1", port)
        return self.driver

    def close(self) -> None:
        if self.driver:
            self.driver.close()
            self.driver = None
        if self._proc:
            self._proc.terminate()
            with suppress(subprocess.TimeoutExpired):
                self._proc.wait(timeout=5)
            self._proc.kill()
            self._proc = None
        if self._profile_dir:
            shutil.rmtree(self._profile_dir, ignore_errors=True)
            self._profile_dir = None

    def __enter__(self) -> CDPDriver:
        return self.start()

    def __exit__(self, *_) -> None:
        self.close()
