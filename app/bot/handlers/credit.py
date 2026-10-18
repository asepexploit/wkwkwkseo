from telegram import Update
from telegram.ext import ContextTypes

from app.bot.middlewares.auth import ensure_registered
from app.services.credit_service import get_credit
from app.database.connection import get_db


async def credit_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await ensure_registered(update)
    kredit = await get_credit(update.effective_user.id)
    msg = (
        "💰 <b>Saldo Kredit</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Kredit kamu saat ini: <b>{kredit} kredit</b>\n"
        "\n"
        "1 kredit = 1 domain = semua metrik\n"
        "\n"
        "Ketik /topup untuk isi ulang."
    )
    if update.message:
        await update.message.reply_text(msg, parse_mode="HTML")
    else:
        await update.callback_query.edit_message_text(msg, parse_mode="HTML")


async def history_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await ensure_registered(update)
    tg_id = update.effective_user.id
    db = await get_db()

    async with db.execute(
        """SELECT h.domain, h.da, h.dr, h.checked_at
           FROM history_cek h
           JOIN users u ON u.id = h.user_id
           WHERE u.telegram_id = ?
           ORDER BY h.checked_at DESC LIMIT 10""",
        (tg_id,),
    ) as cur:
        rows = await cur.fetchall()

    if not rows:
        await update.message.reply_text("Belum ada history cek.")
        return

    lines = "\n".join(
        f"  {i+1}. {r['domain']}  DA:{r['da']}  DR:{r['dr']}"
        for i, r in enumerate(rows)
    )
    msg = (
        "╔══════════════════════╗\n"
        "║   📋 HISTORY CEK     ║\n"
        "╚══════════════════════╝\n"
        "\n"
        f"{lines}"
    )
    await update.message.reply_text(f"<pre>{msg}</pre>", parse_mode="HTML")
