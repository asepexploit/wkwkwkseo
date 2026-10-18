def format_result(domain: str, da, pa, ss, age, dr, bc, bc_df, rd, rd_df, kredit: int,
                  from_cache: bool = False, cached_at: str | None = None) -> str:
    ss_str = str(ss) if ss is not None else "N/A"
    bc_df_str = f" ({bc_df}% dofollow)" if bc_df is not None else ""
    rd_df_str = f" ({rd_df}% dofollow)" if rd_df is not None else ""

    cache_block = ""
    if from_cache:
        tanggal = _fmt_tanggal_wib(cached_at)
        cache_block = (
            f"\n<code>{'─' * 26}</code>\n"
            f"<i>Data dari cache · {tanggal}</i>\n"
            f"<i>Cek ulang akan memotong 1 kredit</i>"
        )

    return (
        f"🔎 <b>wkwkwkseo</b>\n"
        f"<code>{'─' * 26}</code>\n"
        f"🌐 <b>{domain}</b>\n"
        f"<code>{'─' * 26}</code>\n"
        f"\n"
        f"<b>DA</b> : <code>{da}</code>  |  <b>PA</b> : <code>{pa}</code>\n"
        f"<b>SS</b> : <code>{ss_str}</code>\n"
        f"\n"
        f"<i>— Ahrefs —</i>\n"
        f"<b>DR</b> : <code>{dr}</code>\n"
        f"<b>BC</b> : <code>{bc}</code>{bc_df_str}\n"
        f"<b>RD</b> : <code>{rd}</code>{rd_df_str}\n"
        f"\n"
        f"<b>Age</b> : <code>{age}</code>\n"
        f"\n"
        f"<code>{'─' * 26}</code>\n"
        f"💳 Kredit: <b>{kredit}</b>"
        f"{cache_block}"
    )


def _fmt_tanggal_wib(cached_at: str | None) -> str:
    if not cached_at:
        return "—"
    try:
        from datetime import datetime, timezone, timedelta
        wib = timezone(timedelta(hours=7))
        # cached_at dari SQLite biasanya "YYYY-MM-DD HH:MM:SS"
        dt = datetime.strptime(str(cached_at)[:19], "%Y-%m-%d %H:%M:%S")
        dt = dt.replace(tzinfo=timezone.utc).astimezone(wib)
        BULAN = ["", "Jan", "Feb", "Mar", "Apr", "Mei", "Jun",
                 "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]
        return f"{dt.day} {BULAN[dt.month]} {dt.year}, {dt.hour:02d}:{dt.minute:02d} WIB"
    except Exception:
        return str(cached_at)[:16]


def format_welcome(username: str) -> str:
    name = f"@{username}" if username else "kamu"
    return (
        "🔎 <b>wkwkwkseo</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        f"👋 Halo, <b>{name}</b>!\n"
        "\n"
        "Cek metrik domain SEO lengkap\n"
        "hanya dalam <b>satu kali kirim</b>.\n"
        "\n"
        "  <b>DA · PA · SS · DR · BC · RD · Age</b>\n"
        "\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🎁 Kamu dapat <b>5 kredit gratis</b>!\n"
        "Kirim domain sekarang → <code>google.com</code>"
    )


def _is_clean_ss(ss: str) -> bool:
    try:
        val = float(ss.replace("%", ""))
        return val <= 30
    except ValueError:
        return True
