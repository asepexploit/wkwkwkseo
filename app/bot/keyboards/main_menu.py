from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from app.utils.constants import ADMIN_USERNAME


def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔎 Cek Domain",      callback_data="menu_cek"),
            InlineKeyboardButton("💳 Top Up Kredit",   callback_data="menu_topup"),
        ],
        [
            InlineKeyboardButton("📋 History Cek",     callback_data="menu_history"),
            InlineKeyboardButton("💰 Saldo Kredit",    callback_data="menu_kredit"),
        ],
        [
            InlineKeyboardButton("📦 Paket Harga",     callback_data="menu_paket"),
            InlineKeyboardButton("💬 Hubungi Admin",   url=f"https://t.me/{ADMIN_USERNAME}"),
        ],
    ])
