import os
from telegram import Update
from telegram.ext import ContextTypes

from app.bot.middlewares.auth import ensure_registered
from app.bot.keyboards.main_menu import main_menu_keyboard
from app.utils.formatter import format_welcome

BANNER_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "..", "img", "banner.png")


async def start_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    _, is_new = await ensure_registered(update)
    username = update.effective_user.username
    msg = format_welcome(username)

    with open(os.path.abspath(BANNER_PATH), "rb") as f:
        await update.message.reply_photo(
            photo=f,
            caption=msg,
            parse_mode="HTML",
            reply_markup=main_menu_keyboard(),
        )
