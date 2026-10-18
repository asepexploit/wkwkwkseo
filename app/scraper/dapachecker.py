import json
import logging
import os
import time

from app.scraper.chrome_session import CDPDriver
from app.utils.constants import DAPACHECKER_COOKIES_PATH

logger = logging.getLogger(__name__)


def scrape_moz(driver: CDPDriver, domain: str) -> dict:
    """Cek DA/PA/SS/Age. Fallback chain: dapachecker → smallseotools → guestpostlinks."""
    result = _try_dapachecker(driver, domain)
    if result:
        return result
    print("[fallback] coba smallseotools...")
    result = _try_smallseotools(driver, domain)
    if result:
        return result
    print("[fallback] coba guestpostlinks...")
    result = _try_guestpostlinks(driver, domain)
    if result:
        return result
    print(f"[fallback] semua sumber gagal untuk {domain}")
    return {"da": None, "pa": None, "ss": None, "age": None}


# ─── dapachecker.org ─────────────────────────────────────────────────────────

def _try_dapachecker(driver: CDPDriver, domain: str) -> dict | None:
    cookies = _load_cookies()
    if not cookies:
        print("[dapachecker] tidak ada cookies, skip ke fallback")
        return None

    applied = driver.set_cookies(cookies)
    print(f"[dapachecker] {applied}/{len(cookies)} cookie berhasil diinjeksi")
    print("[dapachecker] membuka halaman...")
    try:
        driver.goto("https://www.dapachecker.org/", timeout_ms=60000)
    except Exception as e:
        print(f"[dapachecker] goto error: {e}")
        return None

    # Tunggu #urls (hanya muncul di halaman asli, bukan halaman Cloudflare challenge)
    textarea_found = False
    for _ in range(35):
        time.sleep(1)
        ok = driver.evaluate(
            "(function(){try{return !!document.querySelector('#urls,textarea');}catch(e){return false;}})()"
        )
        if ok:
            textarea_found = True
            break
    if not textarea_found:
        print(f"[dapachecker] textarea tidak muncul setelah 35s, URL: {driver.current_url()[:80]}")
        return None

    driver.evaluate(
        f"(function(){{try{{"
        f"var ta=document.querySelector('#urls,textarea');"
        f"var ns=Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype,'value');"
        f"if(ns&&ns.set)ns.set.call(ta,{json.dumps(domain)});"
        f"else ta.value={json.dumps(domain)};"
        f"ta.dispatchEvent(new Event('input',{{bubbles:true}}));"
        f"ta.dispatchEvent(new Event('change',{{bubbles:true}}));"
        f"}}catch(e){{}}}})()"
    )
    time.sleep(0.5)
    driver.evaluate(
        "(function(){try{"
        "var btn=document.querySelector('#tool-button-container .tool-button,button[type=\"submit\"],input[type=\"submit\"],button.btn');"
        "if(btn)btn.click();"
        "}catch(e){};})()"
    )
    print("[dapachecker] polling hasil...")
    return _poll_dapachecker(driver, domain)


_AGE_GRACE_ROUNDS = 20

_RESULT_JS = (
    "(function(domain){{"
    "var needle=domain.trim().toLowerCase().replace(/^www\\./, '');"
    "var rows=document.querySelectorAll('#result-table tbody tr[data-domain]');"
    "for(var i=0;i<rows.length;i++){{"
    "var d=(rows[i].getAttribute('data-domain')||'').trim().toLowerCase().replace(/^www\\./, '');"
    "if(d!==needle)continue;"
    "var daEl=rows[i].querySelector('.da');"
    "var paEl=rows[i].querySelector('.pa');"
    "var ssEl=rows[i].querySelector('.ss');"
    "var ageEl=rows[i].querySelector('.age');"
    "if(!daEl||!paEl)return null;"
    "return{{da:daEl.innerText,pa:paEl.innerText,"
    "ss:ssEl?ssEl.innerText:'',age:ageEl?ageEl.innerText:''}};"
    "}}"
    "return null;"
    "}})('{domain}')"
)


def _lookup(driver: CDPDriver, domain: str) -> dict | None:
    needle = domain.strip().lower().removeprefix("www.")
    js = (
        "(function(){"
        f"var needle={json.dumps(needle)};"
        "var rows=document.querySelectorAll('#result-table tbody tr[data-domain]');"
        "for(var i=0;i<rows.length;i++){"
        "var d=(rows[i].getAttribute('data-domain')||'').trim().toLowerCase().replace(/^www\\./,'');"
        "if(d!==needle)continue;"
        "var daEl=rows[i].querySelector('.da');"
        "var paEl=rows[i].querySelector('.pa');"
        "var ssEl=rows[i].querySelector('.ss');"
        "var ageEl=rows[i].querySelector('.age');"
        "if(!daEl||!paEl)return null;"
        "return{da:(daEl.innerText||'').trim(),pa:(paEl.innerText||'').trim(),"
        "ss:ssEl?(ssEl.innerText||'').trim():'',age:ageEl?(ageEl.innerText||'').trim():''};"
        "}"
        "return null;"
        "})()"
    )
    try:
        return driver.evaluate(js)
    except Exception:
        return None


def _poll_dapachecker(driver: CDPDriver, domain: str) -> dict | None:
    da_pa_ready_since = None
    for i in range(40):
        time.sleep(1)
        try:
            # Paywall / rate limit → langsung fallback
            paywall = driver.evaluate(
                "(function(){try{var p=document.querySelector('#paywall');"
                "return p&&p.style.display!=='none';}catch(e){return false;}})()"
            )
            if paywall:
                print("[dapachecker] paywall/rate limit terdeteksi, fallback...")
                return None

            entry = _lookup(driver, domain)
            if not entry:
                continue
            da_raw = entry.get("da", "")
            pa_raw = entry.get("pa", "")
            # DA berisi SVG "Missing" = rate limit, bukan angka
            if da_raw in (None, "") or "<svg" in str(da_raw):
                print("[dapachecker] DA missing (rate limit), fallback...")
                return None
            if pa_raw in (None, "") or "<svg" in str(pa_raw):
                continue
            # DA/PA sudah ada, catat kapan pertama kali
            if da_pa_ready_since is None:
                da_pa_ready_since = i
            age_raw = entry.get("age", "")
            if age_raw in (None, "") and (i - da_pa_ready_since) < _AGE_GRACE_ROUNDS:
                continue  # tunggu age menyusul
            try:
                da = int(str(da_raw).strip())
                pa = int(str(pa_raw).strip())
            except Exception:
                continue
            ss_raw = str(entry.get("ss") or "").strip().rstrip("%") or None
            try:
                ss_int = int(ss_raw) if ss_raw else None
            except Exception:
                ss_int = None
            ss_str = f"{ss_int}%" if ss_int is not None else None
            age = str(age_raw).strip() or None
            print(f"[dapachecker] BERHASIL: DA={da} PA={pa} SS={ss_str} Age={age}")
            return {"da": da, "pa": pa, "ss": ss_str, "age": age}
        except Exception:
            pass
    return None


# ─── CF Turnstile klik tanpa CaptchaAI ──────────────────────────────────────

def _click_cf_and_submit(driver: CDPDriver, submit_js: str) -> None:
    """Tunggu CF iframe muncul, klik, tunggu 10 detik, klik lagi, lalu submit."""
    # Tunggu iframe muncul dulu
    for i in range(40):
        time.sleep(1)
        if driver.click_cf_iframe():
            print(f"[cf] klik pertama ({i+1}s)")
            break
    # Selalu tunggu 10 detik dan klik lagi (tidak cek status)
    time.sleep(10)
    driver.click_cf_iframe()
    print("[cf] klik kedua, submit...")
    driver.evaluate(submit_js)


# ─── smallseotools.com ───────────────────────────────────────────────────────

def _try_smallseotools(driver: CDPDriver, domain: str) -> dict | None:
    url = "https://smallseotools.com/id/domain-authority-checker/"
    try:
        driver.goto(url, timeout_ms=60000)
        # Tunggu textarea muncul (setelah CF auto-resolve)
        for _ in range(35):
            time.sleep(1)
            ok = driver.evaluate(
                "(function(){try{return !!document.querySelector('textarea');}catch(e){return false;}})()"
            )
            if ok:
                break

        driver.evaluate(
            f"(function(){{try{{var ta=document.querySelector('textarea');"
            f"ta.value={json.dumps(domain)};"
            f"ta.dispatchEvent(new Event('input',{{bubbles:true}}));}}catch(e){{}}}})()"
        )

        # Klik CF Turnstile checkbox (tunggu iframe muncul max 40 detik)
        _click_cf_and_submit(driver,
            submit_js="(function(){try{check_validation();}catch(e){};})()"
        )
        return _poll_smallseo(driver, domain)
    except Exception as e:
        logger.error(f"smallseotools error: {e}")
        return None


def _poll_smallseo(driver: CDPDriver, domain: str) -> dict | None:
    for _ in range(40):
        time.sleep(1)
        try:
            rows = driver.evaluate(
                "(function(){try{"
                "var rows=Array.from(document.querySelectorAll('#excel_report_section tr'));"
                "return rows.map(function(r){"
                "var tds=Array.from(r.querySelectorAll('td'));"
                "return tds.map(function(td){return(td.innerText||'').trim();});"
                "});}catch(e){return[];}})()"
            )
            if not rows:
                continue
            for row in rows:
                if len(row) >= 3 and domain.lower() in row[0].lower():
                    try:
                        da = int(row[1].replace(",", ""))
                        pa = int(row[2].replace(",", ""))
                        return {"da": da, "pa": pa, "ss": None, "age": None}
                    except Exception:
                        pass
        except Exception:
            pass
    return None


# ─── guestpostlinks.net ──────────────────────────────────────────────────────

def _try_guestpostlinks(driver: CDPDriver, domain: str) -> dict | None:
    url = "https://tools.guestpostlinks.net/id/bulk-cek-da-pa/"
    try:
        driver.goto(url, timeout_ms=60000)
        # Tunggu textarea muncul
        for _ in range(35):
            time.sleep(1)
            ok = driver.evaluate(
                "(function(){try{return !!document.querySelector('textarea');}catch(e){return false;}})()"
            )
            if ok:
                break

        driver.evaluate(
            f"(function(){{try{{var ta=document.querySelector('textarea');"
            f"ta.value={json.dumps(domain)};"
            f"ta.dispatchEvent(new Event('input',{{bubbles:true}}));}}catch(e){{}}}})()"
        )

        # Klik CF Turnstile checkbox lalu klik submit
        _click_cf_and_submit(driver,
            submit_js="(function(){try{var btn=document.querySelector('#DAPAformsend');if(btn)btn.click();}catch(e){};})()"
        )
        return _poll_guestpost(driver, domain)
    except Exception as e:
        logger.error(f"guestpostlinks error: {e}")
        return None


def _poll_guestpost(driver: CDPDriver, domain: str) -> dict | None:
    needle = domain.strip().lower().removeprefix("www.")
    for _ in range(20):
        time.sleep(1)
        try:
            result = driver.evaluate(
                f"(function(){{"
                f"var needle={json.dumps(needle)};"
                f"var rows=document.querySelectorAll('#dapa_tbl tbody tr');"
                f"for(var i=0;i<rows.length;i++){{"
                f"var a=rows[i].querySelector('td.url a');"
                f"if(!a)continue;"
                f"var url=(a.getAttribute('href')||'').replace(/https?:\\/\\//,'').replace(/^www\\./,'').replace(/\\/$/,'').toLowerCase();"
                f"if(url.indexOf(needle)===-1)continue;"
                f"var daEl=rows[i].querySelector('td.da .v');"
                f"var paEl=rows[i].querySelector('td.pa .v');"
                f"var ssEl=rows[i].querySelector('td.ss .dapa-ss');"
                f"if(!daEl||!paEl)continue;"
                f"var da=(daEl.innerText||'').trim();"
                f"var pa=(paEl.innerText||'').trim();"
                f"var ss=ssEl?(ssEl.innerText||'').trim():null;"
                f"if(!da||!pa)continue;"
                f"return{{da:da,pa:pa,ss:ss}};"
                f"}}"
                f"return null;"
                f"}})()"
            )
            if not result:
                continue
            try:
                da = int(str(result["da"]).replace(",", ""))
                pa = int(str(result["pa"]).replace(",", ""))
                ss_raw = result.get("ss")
                ss = f"{int(ss_raw)}%" if ss_raw and str(ss_raw).isdigit() else None
                print(f"[guestpostlinks] BERHASIL: DA={da} PA={pa} SS={ss}")
                return {"da": da, "pa": pa, "ss": ss, "age": None}
            except Exception:
                pass
        except Exception:
            pass
    return None


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _load_cookies() -> list:
    path = DAPACHECKER_COOKIES_PATH
    print(f"[dapachecker] baca cookies dari: {path}")
    if not os.path.exists(path):
        print(f"[dapachecker] FILE TIDAK ADA: {path}")
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        cookies = data.get("cookies", data) if isinstance(data, dict) else data
        # Kirim cookie as-is (jangan strip field) supaya expirationDate ikut ke set_cookies
        valid = [c for c in cookies if isinstance(c, dict) and c.get("name") and c.get("domain")]
        print(f"[dapachecker] {len(valid)} cookie dimuat dari {path}")
        return valid
    except Exception as e:
        logger.error(f"Gagal baca cookies dapachecker: {e}")
        return []


def _fmt_ss(ss: str | None) -> str | None:
    if not ss:
        return None
    ss = ss.strip()
    if "%" not in ss:
        ss = ss + "%"
    return ss
