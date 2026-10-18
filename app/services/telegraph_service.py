import asyncio
from telegraph import Telegraph

_telegraph: Telegraph | None = None


def _get_telegraph() -> Telegraph:
    global _telegraph
    if _telegraph is None:
        _telegraph = Telegraph()
        _telegraph.create_account(short_name="wkwkwkseo", author_name="wkwkwkseo")
    return _telegraph


def _is_clean_ss(ss: str) -> bool:
    try:
        return float(ss.replace("%", "")) <= 30
    except Exception:
        return True


def _ss_color(ss: str) -> str:
    try:
        val = float(str(ss).replace("%", ""))
        if val <= 10:
            return "#27ae60"
        if val <= 30:
            return "#f39c12"
        return "#e74c3c"
    except Exception:
        return "#888"


def _score_color(val) -> str:
    try:
        v = int(val)
        if v >= 70:
            return "#27ae60"
        if v >= 40:
            return "#f39c12"
        return "#e74c3c"
    except Exception:
        return "#888"


def build_html(domain: str, da, pa, ss, age, dr, bc, bc_df, rd, rd_df, backlinks: list) -> str:
    ss_str = str(ss) if ss else "N/A"
    ss_label = "✅ Clean" if _is_clean_ss(ss_str) else "🚨 Spam"
    bc_df_str = f" ({bc_df}% dofollow)" if bc_df is not None else ""
    rd_df_str = f" ({rd_df}% dofollow)" if rd_df is not None else ""

    # Summary section
    html = (
        f"<p>🌐 <strong>{domain}</strong></p>"
        f"<p>"
        f"DA <strong>{da}</strong> · "
        f"PA <strong>{pa}</strong> · "
        f"SS <strong>{ss_str}</strong> {ss_label}"
        f"</p>"
        f"<p>"
        f"DR <strong>{dr}</strong> · "
        f"BC <strong>{bc}</strong>{bc_df_str} · "
        f"RD <strong>{rd}</strong>{rd_df_str}"
        f"</p>"
        f"<p>Age <strong>{age}</strong></p>"
        f"<hr/>"
    )

    # Backlink list
    html += f"<h4>🔗 Top Backlinks (Ahrefs)</h4>"
    if backlinks:
        for bl in backlinks:
            title  = bl.get("ref_title") or bl.get("page") or "–"
            url    = bl.get("ref_url")   or bl.get("url")  or "#"
            anchor = bl.get("anchor_text") or bl.get("anchor") or "–"
            target = bl.get("target_url")  or bl.get("target") or ""
            html += (
                f"<p>"
                f"<strong>DR {bl['dr']}</strong> — "
                f"<a href='{url}'>{title}</a>"
                f"<br/>"
                f"Anchor: <em>{anchor}</em>"
                + (f" → {target}" if target else "")
                + f"</p>"
            )
    else:
        html += "<p><em>Data backlink belum tersedia.</em></p>"

    html += (
        f"<hr/>"
        f"<p><em>Powered by <strong>wkwkwkseo</strong></em></p>"
    )
    return html


async def create_telegraph_page(domain: str, da, pa, ss, age, dr, bc, bc_df, rd, rd_df, backlinks: list = None) -> str:
    loop = asyncio.get_event_loop()
    html = build_html(domain, da, pa, ss, age, dr, bc, bc_df, rd, rd_df, backlinks or [])

    def _create():
        t = _get_telegraph()
        response = t.create_page(
            title=f"Domain Report: {domain}",
            html_content=html,
            author_name="wkwkwkseo",
        )
        return f"https://telegra.ph/{response['path']}"

    url = await loop.run_in_executor(None, _create)
    return url
