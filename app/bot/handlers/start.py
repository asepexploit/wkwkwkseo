import os
from telegram import Update
from telegram.ext import ContextTypes

from app.bot.middlewares.auth import ensure_registered
from app.bot.keyboards.main_menu import main_menu_keyboard
from app.services.credit_service import claim_daily, get_credit, DAILY_CREDIT
from app.utils.formatter import format_welcome

BANNER_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "..", "img", "banner.png")


async def start_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    _, is_new = await ensure_registered(update)
    username = update.effective_user.username

    # Cek daily reward
    got_daily = await claim_daily(tg_id)
    kredit = await get_credit(tg_id)

    msg = format_welcome(username)
    if got_daily:
        msg += f"\n\n🎁 <b>+{DAILY_CREDIT} kredit harian!</b> Total kredit kamu: <b>{kredit}</b>"
    elif not is_new:
        msg += f"\n\n💳 Kredit kamu: <b>{kredit}</b>"

    try:
        with open(os.path.abspath(BANNER_PATH), "rb") as f:
            await update.message.reply_photo(
                photo=f,
                caption=msg,
                parse_mode="HTML",
                reply_markup=main_menu_keyboard(),
            )
    except Exception:
        await update.message.reply_text(
            msg,
            parse_mode="HTML",
            reply_markup=main_menu_keyboard(),
        )
