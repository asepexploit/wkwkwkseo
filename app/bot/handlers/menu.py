from telegram import Update
from telegram.ext import ContextTypes

from app.bot.keyboards.topup_menu import topup_keyboard
from app.bot.keyboards.main_menu import main_menu_keyboard
from app.services.credit_service import get_credit
from app.utils.constants import PAKET
from app.database.connection import get_db


async def _edit(query, text: str, parse_mode="HTML", reply_markup=None):
    """Edit pesan: pakai edit_message_caption kalau ada foto, edit_message_text kalau tidak."""
    if query.message and query.message.photo:
        await query.edit_message_caption(
            caption=text, parse_mode=parse_mode, reply_markup=reply_markup
        )
    else:
        await query.edit_message_text(
            text=text, parse_mode=parse_mode, reply_markup=reply_markup
        )


async def menu_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action = query.data
    tg_id = query.from_user.id

    if action == "menu_cek":
        await _edit(
            query,
            "✏️ <b>Cek Domain</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "Kirim nama domain yang ingin dicek.\n\n"
            "Contoh:\n"
            "<code>google.com</code>\n"
            "<code>tokopedia.com</code>",
        )

    elif action == "menu_topup":
        lines = "\n".join(f"  ▸ {v['label']}" for v in PAKET.values())
        msg = (
            "💳 <b>Top Up Kredit</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "Pilih paket kredit di bawah:\n\n"
            f"{lines}"
        )
        await _edit(query, msg, reply_markup=topup_keyboard())

    elif action == "menu_kredit":
        kredit = await get_credit(tg_id)
        msg = (
            "💰 <b>Saldo Kredit</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Kredit kamu saat ini: <b>{kredit} kredit</b>\n\n"
            "1 kredit = 1 domain = semua metrik\n\n"
            "Ketik /topup untuk isi ulang."
        )
        await _edit(query, msg, reply_markup=_back_keyboard())

    elif action == "menu_history":
        db = await get_db()
        async with db.execute(
            """SELECT h.domain, h.da, h.pa, h.ss, h.dr, h.bc, h.rd, h.age, h.checked_at
               FROM history_cek h
               JOIN users u ON u.id = h.user_id
               WHERE u.telegram_id = ?
               ORDER BY h.checked_at DESC LIMIT 10""",
            (tg_id,),
        ) as cur:
            rows = await cur.fetchall()

        if not rows:
            await _edit(
                query,
                "📋 <b>History Cek</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "Belum ada history cek.",
                reply_markup=_back_keyboard(),
            )
            return

        from datetime import datetime, timezone, timedelta
        def _fmt_wib(dt_str):
            if not dt_str:
                return "—"
            try:
                wib = timezone(timedelta(hours=7))
                dt = datetime.strptime(str(dt_str)[:19], "%Y-%m-%d %H:%M:%S")
                dt = dt.replace(tzinfo=timezone.utc).astimezone(wib)
                BULAN = ["","Jan","Feb","Mar","Apr","Mei","Jun","Jul","Agu","Sep","Okt","Nov","Des"]
                return f"{dt.day} {BULAN[dt.month]} {dt.year}, {dt.hour:02d}:{dt.minute:02d}"
            except Exception:
                return str(dt_str)[:16]

        sep = "─" * 24
        parts = [f"📋 <b>History Cek</b>  <i>(10 terakhir)</i>\n<code>{sep}</code>"]
        for i, r in enumerate(rows):
            da  = r["da"]  or "—"
            pa  = r["pa"]  or "—"
            ss  = r["ss"]  or "—"
            dr  = r["dr"]  or "—"
            bc  = r["bc"]  or "—"
            rd  = r["rd"]  or "—"
            age = r["age"] or "—"
            tgl = _fmt_wib(r["checked_at"])
            parts.append(
                f"<b>{i+1}.</b> <code>{r['domain']}</code>\n"
                f"  DA <b>{da}</b>  PA <b>{pa}</b>  SS <b>{ss}</b>\n"
                f"  DR <b>{dr}</b>  BC <b>{bc}</b>  RD <b>{rd}</b>\n"
                f"  Age <b>{age}</b>\n"
                f"  <i>🕐 {tgl} WIB</i>"
            )
        parts.append(f"<code>{sep}</code>")
        await _edit(
            query,
            "\n".join(parts),
            reply_markup=_back_keyboard(),
        )

    elif action == "menu_paket":
        lines = "\n".join(
            f"  ▸ <b>{v['label']}</b>"
            for v in PAKET.values()
        )
        await _edit(
            query,
            "📦 <b>Paket Harga</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{lines}\n\n"
            "Ketik /topup untuk beli kredit.",
            reply_markup=_back_keyboard(),
        )

    elif action == "menu_back":
        from app.utils.formatter import format_welcome
        msg = format_welcome(query.from_user.username)
        await _edit(query, msg, reply_markup=main_menu_keyboard())


def _back_keyboard():
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("⬅️ Kembali", callback_data="menu_back")
    ]])
