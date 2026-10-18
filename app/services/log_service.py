import logging
from app.utils.constants import LOG_CHANNEL_ID

logger = logging.getLogger(__name__)

_bot = None


def init_log_bot(bot):
    global _bot
    _bot = bot


async def log_cek(tg_id: int, username: str | None, domain: str, result: dict, from_cache: bool):
    if not _bot or not LOG_CHANNEL_ID:
        return
    try:
        name = f"@{username}" if username else f"id:{tg_id}"
        status = "📦 Cache" if from_cache else "🔍 Scrape baru"
        da  = result.get("da",  "N/A")
        pa  = result.get("pa",  "N/A")
        dr  = result.get("dr",  "N/A")
        bc  = result.get("bc",  "N/A")
        rd  = result.get("rd",  "N/A")
        ss  = result.get("ss",  "N/A")
        age = result.get("age", "N/A")

        msg = (
            f"<b>CEK DOMAIN</b> · {status}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 User  : {name} (<code>{tg_id}</code>)\n"
            f"🌐 Domain: <code>{domain}</code>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"DA <b>{da}</b>  PA <b>{pa}</b>  SS <b>{ss}</b>\n"
            f"DR <b>{dr}</b>  BC <b>{bc}</b>  RD <b>{rd}</b>\n"
            f"Age <b>{age}</b>"
        )
        await _bot.send_message(chat_id=LOG_CHANNEL_ID, text=msg, parse_mode="HTML")
    except Exception as e:
        logger.warning(f"[log_channel] gagal kirim log: {e}")
