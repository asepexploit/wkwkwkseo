import logging
import time

from app.scraper.chrome_session import CDPDriver

logger = logging.getLogger(__name__)

_JS_FIND_METRICS = (
    "(function(){"
    "function isLeaf(el){return el&&el.children&&el.children.length===0;}"
    "function findDofollowPct(container){"
    "var ps=container.querySelectorAll('p');"
    "for(var i=0;i<ps.length;i++){"
    "if(!isLeaf(ps[i]))continue;"
    "var m=/(\\d+)%\\s*dofollow/i.exec((ps[i].textContent||'').trim());"
    "if(m)return m[1];"
    "}"
    "return null;"
    "}"
    "function findValueNear(labelText,digitsOnly,withDofollow){"
    "var all=document.querySelectorAll('div,span');"
    "var label=null;"
    "for(var i=0;i<all.length;i++){"
    "if(isLeaf(all[i])&&(all[i].textContent||'').trim()===labelText){label=all[i];break;}"
    "}"
    "if(!label)return[null,null];"
    "var container=label;"
    "for(var j=0;j<7&&container.parentElement;j++)container=container.parentElement;"
    "var candidates=container.querySelectorAll('div,span');"
    "var value=null;"
    "for(var k=0;k<candidates.length;k++){"
    "var el=candidates[k];"
    "if(!isLeaf(el))continue;"
    "var txt=(el.textContent||'').trim();"
    "if(!txt)continue;"
    "if(digitsOnly&&!/^\\d+(\\.\\d+)?$/.test(txt))continue;"
    "var fontSize=parseFloat(window.getComputedStyle(el).fontSize||'0');"
    "if(fontSize>=30){value=txt;break;}"
    "}"
    "var dofollow=withDofollow&&value!==null?findDofollowPct(container):null;"
    "return[value,dofollow];"
    "}"
    "var dr=findValueNear('Peringkat Domain',true,false);"
    "var bc=findValueNear('Backlinks',false,true);"
    "var rd=findValueNear('Situs web penghubung',false,true);"
    "return{dr:dr[0],bc:bc[0],bc_dofollow:bc[1],rd:rd[0],rd_dofollow:rd[1]};"
    "})()"
)

_JS_BACKLINKS = (
    "(function(){"
    "var tables=document.querySelectorAll('table');"
    "for(var t=0;t<tables.length;t++){"
    "var table=tables[t];"
    "var thead=table.querySelector('thead');"
    "if(!thead||(thead.innerText||'').indexOf('DR')===-1)continue;"
    "var rows=table.querySelectorAll('tbody tr');"
    "var out=[];"
    "for(var r=0;r<rows.length;r++){"
    "var tds=rows[r].querySelectorAll('td');"
    "if(tds.length<3)continue;"
    "var drText=(tds[0].innerText||'').trim();"
    "var refAs=tds[1].querySelectorAll('a');"
    "var refTitle=refAs.length>0?(refAs[0].innerText||'').trim():'';"
    "var refUrl=refAs.length>0?refAs[0].getAttribute('href'):'';"
    "var allAs=tds[2].querySelectorAll('a');"
    "var targetUrl=allAs.length>0?allAs[allAs.length-1].getAttribute('href'):'';"
    "var pEl=tds[2].querySelector('p');"
    "var anchorA=pEl?pEl.querySelector('a'):null;"
    "var anchorText=anchorA?(anchorA.innerText||'').trim():null;"
    "out.push({dr:drText,ref_title:refTitle,ref_url:refUrl,anchor_text:anchorText,target_url:targetUrl});"
    "}"
    "return out;"
    "}"
    "return[];"
    "})()"
)


def scrape_ahrefs(driver: CDPDriver, domain: str) -> dict:
    """Scrape DR/BC/RD dari ahrefs.com. Driver harus sudah di-attach ke tab Ahrefs."""
    url = f"https://ahrefs.com/id/backlink-checker/?input={domain}&mode=subdomains"
    print(f"[ahrefs] membuka {url}")
    try:
        driver.goto(url, timeout_ms=60000)
    except Exception as e:
        print(f"[ahrefs] goto error: {e}")
        return _empty()

    print("[ahrefs] cek captcha...")
    # Tunggu CF iframe muncul (bisa butuh 5-35 detik)
    cf_clicked = False
    for i in range(40):
        time.sleep(1)
        clicked = driver.click_cf_iframe()
        if clicked:
            print(f"[ahrefs] CF diklik ({i+1}s), tunggu spinner selesai...")
            cf_clicked = True
            break

    if cf_clicked:
        time.sleep(10)
        driver.click_cf_iframe()
        print("[ahrefs] klik kedua selesai, mulai poll DR...")
    else:
        print("[ahrefs] tidak ada CF iframe, langsung poll DR...")

    _dismiss_popups(driver)
    return _poll_ahrefs(driver)


_JS_DISMISS = """
(function(){
    var btns = document.querySelectorAll('button');
    var keywords = ['accept all', 'accept cookies', 'terima semua', 'setuju', 'agree'];
    for (var i = 0; i < btns.length; i++) {
        var txt = (btns[i].innerText || '').toLowerCase().trim();
        for (var k = 0; k < keywords.length; k++) {
            if (txt.indexOf(keywords[k]) !== -1) {
                btns[i].click();
                return 'clicked:' + btns[i].innerText.trim();
            }
        }
    }
    return null;
})()
"""

_JS_CLOSE_MODAL = """
(function(){
    var closeBtn = document.querySelector('[aria-label="Close"], .modal-close, [data-testid="close-button"]');
    if (closeBtn) { closeBtn.click(); return 'modal closed'; }
    var xBtns = document.querySelectorAll('button');
    for (var i = 0; i < xBtns.length; i++) {
        var txt = (xBtns[i].innerText || '').trim();
        if (txt === '×' || txt === '✕' || txt === 'X') { xBtns[i].click(); return 'x closed'; }
    }
    return null;
})()
"""


def _dismiss_popups(driver: CDPDriver) -> None:
    try:
        result = driver.evaluate(_JS_DISMISS)
        if result:
            print(f"[ahrefs] cookie consent diklik: {result}")
            time.sleep(1.0)
    except Exception:
        pass
    try:
        result = driver.evaluate(_JS_CLOSE_MODAL)
        if result:
            print(f"[ahrefs] modal ditutup: {result}")
            time.sleep(0.5)
    except Exception:
        pass


def _poll_ahrefs(driver: CDPDriver) -> dict:
    for i in range(90):
        time.sleep(0.5)
        if i > 0 and i % 10 == 0:
            print(f"[ahrefs] menunggu DR... ({i//2}s)")
        try:
            result = driver.evaluate(_JS_FIND_METRICS)
            if not result:
                continue
            dr_raw = result.get("dr")
            if not dr_raw:
                continue
            try:
                dr = float(str(dr_raw).strip())
            except Exception:
                continue

            bc = result.get("bc")
            rd = result.get("rd")
            try:
                bc_df = int(result["bc_dofollow"]) if result.get("bc_dofollow") is not None else None
            except Exception:
                bc_df = None
            try:
                rd_df = int(result["rd_dofollow"]) if result.get("rd_dofollow") is not None else None
            except Exception:
                rd_df = None

            backlinks = _poll_backlinks(driver)
            screenshot = driver.screenshot()
            dr_int = int(dr) if dr == int(dr) else dr
            print(f"[ahrefs] BERHASIL: DR={dr_int} BC={bc} RD={rd}")
            return {"dr": dr_int, "bc": bc, "bc_df": bc_df, "rd": rd, "rd_df": rd_df, "backlinks": backlinks, "screenshot": screenshot}
        except Exception as e:
            logger.debug(f"ahrefs poll error: {e}")

    print("[ahrefs] timeout, ambil screenshot anyway...")
    screenshot = driver.screenshot()
    return {**_empty(), "screenshot": screenshot}


def _poll_backlinks(driver: CDPDriver) -> list:
    for _ in range(8):
        time.sleep(0.5)
        try:
            rows = driver.evaluate(_JS_BACKLINKS)
            if rows:
                return rows
        except Exception:
            pass
    return []


def _empty() -> dict:
    return {"dr": None, "bc": None, "bc_df": None, "rd": None, "rd_df": None, "backlinks": [], "screenshot": None}
