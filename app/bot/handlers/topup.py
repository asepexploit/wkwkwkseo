import os
import aiofiles
from telegram import Update
from telegram.ext import ContextTypes

from app.bot.middlewares.auth import ensure_registered
from app.bot.keyboards.topup_menu import topup_keyboard
from app.services.topup_service import create_transaction
from app.services.credit_service import add_credit
from app.services.user_service import get_user
from app.utils.constants import PAKET, REKENING, ADMIN_ID

_pending_topup: dict[int, str] = {}


async def topup_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await ensure_registered(update)
    msg = (
        "💳 <b>Top Up Kredit</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "Pilih paket kredit di bawah ini:"
    )
    await update.message.reply_text(msg, parse_mode="HTML", reply_markup=topup_keyboard())


async def topup_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    paket_key = query.data.replace("topup_", "")
    if paket_key not in PAKET:
        return

    tg_id = query.from_user.id
    _pending_topup[tg_id] = paket_key
    paket = PAKET[paket_key]

    msg = (
        f"💳 <b>Top Up — {paket['label']}</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "Transfer ke rekening berikut:\n"
        f"<pre>{REKENING}</pre>\n"
        "Setelah transfer, kirim <b>foto bukti</b>\n"
        "pembayaran ke sini."
    )
    await query.edit_message_text(msg, parse_mode="HTML")


async def proof_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    paket_key = _pending_topup.get(tg_id)
    if not paket_key:
        return

    photo = update.message.photo[-1]
    file = await ctx.bot.get_file(photo.file_id)
    os.makedirs("storage/proofs", exist_ok=True)
    path = f"storage/proofs/{tg_id}_{photo.file_id}.jpg"
    await file.download_to_drive(path)

    tx = await create_transaction(tg_id, paket_key, path)
    _pending_topup.pop(tg_id, None)

    await update.message.reply_text(
        f"✅ Bukti diterima! ID Transaksi: <code>{tx.id}</code>\n"
        "Menunggu konfirmasi admin.",
        parse_mode="HTML",
    )

    user = await get_user(tg_id)
    paket = PAKET[paket_key]
    await ctx.bot.send_photo(
        chat_id=ADMIN_ID,
        photo=photo.file_id,
        caption=(
            f"📥 Top Up Baru\n"
            f"User: @{update.effective_user.username} ({tg_id})\n"
            f"Paket: {paket['label']}\n"
            f"TX ID: {tx.id}\n\n"
            f"/admin_konfirmasi {tx.id}\n"
            f"/admin_reject {tx.id}"
        ),
    )
