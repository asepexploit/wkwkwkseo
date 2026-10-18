from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from app.utils.constants import PAKET


def topup_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(v["btn"], callback_data=f"topup_{k}")]
        for k, v in PAKET.items()
    ]
    return InlineKeyboardMarkup(buttons)
