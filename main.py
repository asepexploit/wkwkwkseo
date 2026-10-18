from telegram import __version__ as TG_VER
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from telegram.request import HTTPXRequest

from app.utils.logger import setup_logger
from app.database.connection import init_db
from app.queue.manager import QueueManager
from app.bot.handlers.start import start_handler
from app.bot.handlers.check import check_handler, refresh_handler, multipage_handler
from app.bot.handlers.topup import topup_handler, topup_callback, proof_handler
from app.bot.handlers.credit import credit_handler, history_handler
from app.bot.handlers.menu import menu_callback
from app.bot.handlers.admin import (
    admin_konfirmasi, admin_reject, admin_addkredit,
    admin_ban, admin_stats, admin_pending, admin_broadcast
)
from app.utils.constants import BOT_TOKEN

logger = setup_logger(__name__)


def main():
    import asyncio

    async def post_init(app: Application):
        await init_db()
        queue_manager = QueueManager()
        await queue_manager.start()
        app.bot_data["queue_manager"] = queue_manager
        from app.services.log_service import init_log_bot
        init_log_bot(app.bot)
        # Scheduler daily reset kredit setiap 24 jam
        import asyncio as _asyncio
        from app.services.credit_service import run_daily_reset
        async def _daily_loop():
            from datetime import datetime, timedelta, timezone
            while True:
                # Hitung detik sampai 00:00 WIB berikutnya
                wib = timezone(timedelta(hours=7))
                now = datetime.now(wib)
                besok = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
                sisa = (besok - now).total_seconds()
                await _asyncio.sleep(sisa)
                try:
                    await run_daily_reset(app.bot)
                except Exception as e:
                    logger.error(f"[daily] error: {e}")
        _asyncio.create_task(_daily_loop())

    request = HTTPXRequest(connect_timeout=30, read_timeout=60, write_timeout=60, media_write_timeout=120)
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .request(request)
        .concurrent_updates(True)
        .post_init(post_init)
        .build()
    )

    # User commands
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("kredit", credit_handler))
    app.add_handler(CommandHandler("topup", topup_handler))
    app.add_handler(CommandHandler("history", history_handler))

    # Admin commands
    app.add_handler(CommandHandler("admin_konfirmasi", admin_konfirmasi))
    app.add_handler(CommandHandler("admin_reject", admin_reject))
    app.add_handler(CommandHandler("admin_addkredit", admin_addkredit))
    app.add_handler(CommandHandler("admin_ban", admin_ban))
    app.add_handler(CommandHandler("admin_stats", admin_stats))
    app.add_handler(CommandHandler("admin_pending", admin_pending))
    app.add_handler(CommandHandler("admin_broadcast", admin_broadcast))

    # Callback & message handlers
    app.add_handler(CallbackQueryHandler(menu_callback,    pattern="^menu_"))
    app.add_handler(CallbackQueryHandler(topup_callback,  pattern="^topup_"))
    app.add_handler(CallbackQueryHandler(refresh_handler, pattern="^refresh_"))
    app.add_handler(CallbackQueryHandler(multipage_handler, pattern="^multipage_"))
    app.add_handler(MessageHandler(filters.PHOTO, proof_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_handler))

    async def error_handler(update, context):
        logger.error(f"Update {update} caused error: {context.error}", exc_info=context.error)

    app.add_error_handler(error_handler)
    logger.info("Bot started")
    app.run_polling()


if __name__ == "__main__":
    main()
