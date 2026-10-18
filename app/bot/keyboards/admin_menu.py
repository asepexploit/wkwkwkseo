from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def confirm_keyboard(tx_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Konfirmasi", callback_data=f"admin_confirm_{tx_id}"),
            InlineKeyboardButton("❌ Reject",     callback_data=f"admin_reject_{tx_id}"),
        ]
    ])
