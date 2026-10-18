from telegram import Update
from app.services.user_service import get_user


async def is_banned(update: Update) -> bool:
    user = await get_user(update.effective_user.id)
    return bool(user and user.is_banned)
