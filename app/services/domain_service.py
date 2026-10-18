import asyncio
import logging
import re
import threading
from contextlib import suppress
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from app.database.connection import get_db
from app.models.cache import DomainCache
from app.scraper.chrome_session import ChromeSession
from app.scraper.dapachecker import scrape_moz
from app.scraper.ahrefs import scrape_ahrefs
from app.scraper.whois import get_domain_age
from app.utils.constants import CACHE_TTL_HOURS, HEADLESS

logger = logging.getLogger(__name__)

from app.utils.constants import MAX_WORKERS as _MAX_WORKERS
_executor = ThreadPoolExecutor(max_workers=_MAX_WORKERS * 2)
_SCREENSHOT_DIR = Path("screenshots")
_SCREENSHOT_DIR.mkdir(exist_ok=True)


def _screenshot_path(domain: str) -> Path:
    safe = re.sub(r"[^\w\-.]", "_", domain)
    return _SCREENSHOT_DIR / f"{safe}.png"


def _save_screenshot(domain: str, data: bytes) -> None:
    try:
        _screenshot_path(domain).write_bytes(data)
    except Exception as e:
        logger.warning(f"[screenshot] gagal simpan {domain}: {e}")


def _load_screenshot(domain: str) -> bytes | None:
    path = _screenshot_path(domain)
    if path.exists():
        try:
            return path.read_bytes()
        except Exception:
            pass
    return None


def _backlinks_path(domain: str) -> Path:
    safe = re.sub(r"[^\w\-.]", "_", domain)
    return _SCREENSHOT_DIR / f"{safe}_backlinks.json"


def _save_backlinks(domain: str, backlinks: list) -> None:
    try:
        import json
        _backlinks_path(domain).write_text(json.dumps(backlinks, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        logger.warning(f"[backlinks] gagal simpan {domain}: {e}")


def _load_backlinks(domain: str) -> list:
    path = _backlinks_path(domain)
    if path.exists():
        try:
            import json
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []


def _run_both(domain: str) -> dict:
    """1 Chrome, 4 tab paralel:
       Tab 1 = dapachecker    (DA/PA/SS/Age)
       Tab 2 = smallseotools  (DA/PA/SS)
       Tab 3 = guestpostlinks (DA/PA/SS)
       Tab 4 = ahrefs         (DR/BC/RD + screenshot)
    Tab 1-3 race: siapa duluan dapat DA/PA → dipakai, yang lain jalan sampai selesai tapi hasil diabaikan.
    Tab 4 ahrefs jalan independen bersamaan.
    """
    print(f"[scrape] mulai 1 Chrome 3 tab paralel: {domain}")
    session = ChromeSession(headless=HEADLESS)
    driver1 = session.start()  # tab 1 default

    moz_result  = {"da": None, "pa": None, "ss": None, "age": None}
    ahref_result = {"dr": None, "bc": None, "bc_df": None, "rd": None, "rd_df": None, "backlinks": [], "screenshot": None}

    try:
        # Buka window 2, 3, 4 sebelum mulai paralel
        tab2_id = driver1.open_new_tab(new_window=True)
        tab3_id = driver1.open_new_tab(new_window=True)
        tab4_id = driver1.open_new_tab(new_window=True)
        if not tab2_id or not tab3_id or not tab4_id:
            raise RuntimeError("Gagal buka tab")

        driver2 = driver1.connect_tab(tab2_id)  # smallseotools
        driver3 = driver1.connect_tab(tab3_id)  # guestpostlinks
        driver4 = driver1.connect_tab(tab4_id)  # ahrefs
        print(f"[scrape] 4 tab terhubung, mulai paralel...")

        # Siapa duluan dapat DA/PA → set flag, tutup driver lain agar langsung stop
        moz_won = threading.Event()
        moz_drivers = [driver1, driver2, driver3]  # driver untuk DA/PA

        def _kill_moz_losers(winner_driver):
            """Tutup websocket driver yang kalah agar loop polling mereka exit."""
            for d in moz_drivers:
                if d is not winner_driver:
                    with suppress(Exception):
                        d.close()

        def _do_dapachecker():
            from app.scraper.dapachecker import _try_dapachecker
            try:
                r = _try_dapachecker(driver1, domain)
                if r and r.get("da") is not None and not moz_won.is_set():
                    moz_result.update(r)
                    moz_won.set()
                    print(f"[dapachecker] ✓ DA={r.get('da')} PA={r.get('pa')}")
                    _kill_moz_losers(driver1)
            except Exception as e:
                print(f"[dapachecker] error: {e}")

        def _do_smallseo():
            from app.scraper.dapachecker import _try_smallseotools
            try:
                r = _try_smallseotools(driver2, domain)
                if r and r.get("da") is not None and not moz_won.is_set():
                    moz_result.update(r)
                    moz_won.set()
                    print(f"[smallseotools] ✓ DA={r.get('da')} PA={r.get('pa')}")
                    _kill_moz_losers(driver2)
            except Exception as e:
                print(f"[smallseotools] error: {e}")

        def _do_guestpost():
            from app.scraper.dapachecker import _try_guestpostlinks
            try:
                r = _try_guestpostlinks(driver3, domain)
                if r and r.get("da") is not None and not moz_won.is_set():
                    moz_result.update(r)
                    moz_won.set()
                    print(f"[guestpostlinks] ✓ DA={r.get('da')} PA={r.get('pa')}")
                    _kill_moz_losers(driver3)
            except Exception as e:
                print(f"[guestpostlinks] error: {e}")

        def _do_ahrefs():
            try:
                ahref_result.update(scrape_ahrefs(driver4, domain))
                print(f"[ahrefs] ✓ DR={ahref_result.get('dr')} BC={ahref_result.get('bc')}")
            except Exception as e:
                print(f"[ahrefs] error: {e}")

        t1 = threading.Thread(target=_do_dapachecker, name=f"dapa-{domain}",  daemon=True)
        t2 = threading.Thread(target=_do_smallseo,    name=f"small-{domain}", daemon=True)
        t3 = threading.Thread(target=_do_guestpost,   name=f"guest-{domain}", daemon=True)
        t4 = threading.Thread(target=_do_ahrefs,      name=f"ahref-{domain}", daemon=True)
        t1.start(); t2.start(); t3.start(); t4.start()

        # Tunggu salah satu DA/PA berhasil (max 180s), tidak perlu tunggu semua
        moz_won.wait(timeout=180)
        if moz_won.is_set():
            print(f"[scrape] DA/PA race selesai, hasil: DA={moz_result.get('da')}")
        else:
            print(f"[scrape] DA/PA semua gagal/timeout untuk {domain}")

        # Tunggu ahrefs selesai (jalan paralel, mungkin sudah selesai duluan)
        t4.join(timeout=200)

        with suppress(Exception): driver2.close()
        with suppress(Exception): driver3.close()
        with suppress(Exception): driver4.close()

    except Exception as e:
        print(f"[scrape] error setup {domain}: {e}")
    finally:
        session.close()

    return {**moz_result, **ahref_result}


async def check_domain(domain: str, tg_id: int = 0) -> dict:
    cached = await _get_cache(domain)
    if cached:
        print(f"[cache] hit {domain}")
        result = _cache_to_dict(cached)
        result["from_cache"] = True
        return result

    print(f"[check] mulai scrape (1 Chrome 2 tab): {domain}")
    loop = asyncio.get_event_loop()

    _SCRAPE_TIMEOUT = 240  # 4 menit total (moz + ahrefs sekuensial)
    try:
        result = await asyncio.wait_for(
            asyncio.shield(loop.run_in_executor(_executor, _run_both, domain)),
            timeout=_SCRAPE_TIMEOUT,
        )
    except (asyncio.TimeoutError, Exception) as e:
        print(f"[check] timeout/error {domain}: {e}")
        result = {"da": None, "pa": None, "ss": None, "age": None,
                  "dr": None, "bc": None, "bc_df": None, "rd": None, "rd_df": None,
                  "backlinks": [], "screenshot": None}

    if not result.get("age"):
        print(f"[age] age kosong, fallback whatsmydns/whois...")
        result["age"] = await get_domain_age(domain)
        print(f"[age] hasil: {result.get('age')}")

    # Simpan screenshot & backlinks ke disk
    if result.get("screenshot"):
        _save_screenshot(domain, result["screenshot"])
    _save_backlinks(domain, result.get("backlinks") or [])

    result["from_cache"] = False
    await _save_cache(domain, result)
    await _save_history(domain, result, tg_id=tg_id)
    print(f"[check] SELESAI {domain} → DA={result.get('da')} PA={result.get('pa')} DR={result.get('dr')} BC={result.get('bc')} Age={result.get('age')}")
    return result


async def delete_cache(domain: str):
    db = await get_db()
    await db.execute("DELETE FROM cache_domain WHERE domain = ?", (domain,))
    await db.commit()


async def _get_cache(domain: str) -> DomainCache | None:
    db = await get_db()
    async with db.execute(
        "SELECT * FROM cache_domain WHERE domain = ? AND expired_at > datetime('now')", (domain,)
    ) as cur:
        row = await cur.fetchone()
    return DomainCache.from_row(row) if row else None


async def _save_cache(domain: str, data: dict):
    db = await get_db()
    expired_at = (datetime.utcnow() + timedelta(days=36500)).strftime("%Y-%m-%d %H:%M:%S")
    await db.execute(
        """INSERT OR REPLACE INTO cache_domain
           (domain, da, pa, ss, age, dr, bc, bc_df, rd, rd_df, expired_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (domain, data.get("da"), data.get("pa"), data.get("ss"), data.get("age"),
         data.get("dr"), data.get("bc"), data.get("bc_df"), data.get("rd"), data.get("rd_df"), expired_at),
    )
    await db.commit()


async def _save_history(domain: str, data: dict, tg_id: int = 0):
    db = await get_db()
    # Lookup internal user id from telegram_id
    internal_id = 0
    if tg_id:
        async with db.execute("SELECT id FROM users WHERE telegram_id = ?", (tg_id,)) as cur:
            row = await cur.fetchone()
            if row:
                internal_id = row["id"]
    await db.execute(
        """INSERT INTO history_cek (user_id, domain, da, pa, ss, age, dr, bc, bc_df, rd, rd_df)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (internal_id, domain, data.get("da"), data.get("pa"), data.get("ss"), data.get("age"),
         data.get("dr"), data.get("bc"), data.get("bc_df"), data.get("rd"), data.get("rd_df")),
    )
    await db.commit()


def _cache_to_dict(c: DomainCache) -> dict:
    return {"da": c.da, "pa": c.pa, "ss": c.ss, "age": c.age,
            "dr": c.dr, "bc": c.bc, "bc_df": c.bc_df, "rd": c.rd, "rd_df": c.rd_df,
            "backlinks": _load_backlinks(c.domain), "cached_at": str(c.cached_at),
            "screenshot": _load_screenshot(c.domain)}
