from telegram import Update
from app.services.user_service import get_or_create_user


async def ensure_registered(update: Update) -> tuple:
    user = update.effective_user
    return await get_or_create_user(user.id, user.username, user.full_name)
