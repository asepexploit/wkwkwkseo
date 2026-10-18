import asyncio
import time
import urllib.request
import json as _json
import aiohttp
import logging
from app.utils.constants import CAPTCHAAI_API_KEY

logger = logging.getLogger(__name__)

BASE_URL = "https://ocr.captchaai.com"


def solve_turnstile_sync(sitekey: str, page_url: str) -> str | None:
    """Versi sync dari solve_turnstile — dipakai di CDPDriver (sync)."""
    if not CAPTCHAAI_API_KEY:
        logger.warning("CAPTCHAAI_API_KEY kosong — skip CaptchaAI")
        return None
    payload = _json.dumps({
        "clientKey": CAPTCHAAI_API_KEY,
        "task": {"type": "TurnstileTaskProxyless", "websiteURL": page_url, "websiteKey": sitekey},
    }).encode()
    try:
        req = urllib.request.Request(
            f"{BASE_URL}/createTask",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = _json.loads(resp.read().decode())
        if data.get("errorId", 1) != 0:
            logger.error(f"CaptchaAI createTask error: {data.get('errorCode')}")
            return None
        task_id = str(data["taskId"])
    except Exception as e:
        logger.error(f"CaptchaAI createTask exception: {e}")
        return None

    poll_payload = _json.dumps({"clientKey": CAPTCHAAI_API_KEY, "taskId": task_id}).encode()
    time.sleep(15)
    elapsed = 15
    while elapsed < 180:
        try:
            req2 = urllib.request.Request(
                f"{BASE_URL}/getTaskResult",
                data=poll_payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req2, timeout=30) as resp:
                data = _json.loads(resp.read().decode())
            if data.get("errorId", 0) != 0:
                return None
            if data.get("status") == "ready":
                return data.get("solution", {}).get("token")
        except Exception:
            return None
        time.sleep(5)
        elapsed += 5
    return None


async def solve_turnstile(sitekey: str, page_url: str) -> str | None:
    """Solve Cloudflare Turnstile via CaptchaAI. Return token or None on failure."""
    if not CAPTCHAAI_API_KEY:
        logger.warning("CAPTCHAAI_API_KEY kosong — skip CaptchaAI")
        return None

    task_id = await _create_task(sitekey, page_url)
    if not task_id:
        return None

    return await _poll_result(task_id)


async def _create_task(sitekey: str, page_url: str) -> str | None:
    payload = {
        "clientKey": CAPTCHAAI_API_KEY,
        "task": {
            "type": "TurnstileTaskProxyless",
            "websiteURL": page_url,
            "websiteKey": sitekey,
        },
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{BASE_URL}/createTask", json=payload, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                data = await resp.json()
                if data.get("errorId", 1) != 0:
                    logger.error(f"CaptchaAI createTask error: {data.get('errorCode')}")
                    return None
                return str(data["taskId"])
    except Exception as e:
        logger.error(f"CaptchaAI createTask exception: {e}")
        return None


async def _poll_result(task_id: str) -> str | None:
    payload = {"clientKey": CAPTCHAAI_API_KEY, "taskId": task_id}
    elapsed = 0

    await asyncio.sleep(15)
    elapsed += 15

    while elapsed < 180:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{BASE_URL}/getTaskResult", json=payload, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    data = await resp.json()

            if data.get("errorId", 0) != 0:
                logger.error(f"CaptchaAI poll error: {data.get('errorCode')}")
                return None

            status = data.get("status")
            if status == "ready":
                token = data.get("solution", {}).get("token")
                logger.info(f"CaptchaAI token diterima ({len(token or '')} char)")
                return token

            logger.debug(f"CaptchaAI menunggu ({elapsed}s)...")
        except Exception as e:
            logger.error(f"CaptchaAI poll exception: {e}")
            return None

        await asyncio.sleep(5)
        elapsed += 5

    logger.warning(f"CaptchaAI timeout setelah {elapsed}s")
    return None
