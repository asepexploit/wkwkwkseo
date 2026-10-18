from datetime import date, datetime, timedelta
from app.database.connection import get_db

DAILY_CREDIT = 5
MAX_FREE_CREDIT = 5  # kredit maksimal dari daily reward (tidak nambah jika sudah >= ini)


async def claim_daily(telegram_id: int) -> bool:
    """Set kredit ke MAX_FREE_CREDIT jika belum claim hari ini. Return True jika berhasil."""
    db = await get_db()
    today = date.today().isoformat()
    async with db.execute("SELECT kredit, last_daily FROM users WHERE telegram_id = ?", (telegram_id,)) as cur:
        row = await cur.fetchone()
    if not row:
        return False
    if row["last_daily"] == today:
        return False
    # Set ke MAX_FREE_CREDIT, tapi jika sudah punya lebih dari itu jangan dikurangi
    kredit_baru = max(row["kredit"], MAX_FREE_CREDIT)
    # Kalau kredit sudah >= MAX_FREE_CREDIT, tetap update last_daily tapi tidak tambah
    await db.execute(
        "UPDATE users SET kredit = ?, last_daily = ? WHERE telegram_id = ?",
        (kredit_baru, today, telegram_id),
    )
    await db.commit()
    return kredit_baru > row["kredit"]  # True hanya jika kredit benar-benar bertambah


async def run_daily_reset(bot) -> None:
    """Jalankan setiap 24 jam: set kredit ke 5 untuk semua user aktif, kirim notif."""
    import logging
    logger = logging.getLogger(__name__)
    db = await get_db()
    today = date.today().isoformat()

    # Ambil semua user yang belum dapat daily hari ini dan tidak banned
    async with db.execute(
        "SELECT telegram_id, kredit FROM users WHERE (last_daily IS NULL OR last_daily < ?) AND (is_banned = 0 OR is_banned IS NULL)",
        (today,),
    ) as cur:
        rows = await cur.fetchall()

    berhasil = 0
    for row in rows:
        tg_id = row["telegram_id"]
        kredit_lama = row["kredit"]
        kredit_baru = max(kredit_lama, MAX_FREE_CREDIT)
        await db.execute(
            "UPDATE users SET kredit = ?, last_daily = ? WHERE telegram_id = ?",
            (kredit_baru, today, tg_id),
        )
        # Kirim notif hanya jika kredit benar-benar bertambah
        if kredit_baru > kredit_lama:
            try:
                await bot.send_message(
                    chat_id=tg_id,
                    text=(
                        f"🎁 <b>Kredit harian kamu sudah diisi ulang!</b>\n\n"
                        f"Kamu mendapat <b>+{kredit_baru - kredit_lama} kredit</b>\n"
                        f"Total kredit sekarang: <b>{kredit_baru}</b>\n\n"
                        f"<i>Kredit harian maksimal {MAX_FREE_CREDIT}. "
                        f"Gunakan sebelum reset besok!</i>"
                    ),
                    parse_mode="HTML",
                )
                berhasil += 1
            except Exception as e:
                logger.debug(f"[daily] gagal kirim notif ke {tg_id}: {e}")

    await db.commit()
    logger.info(f"[daily] reset selesai: {berhasil}/{len(rows)} user diberi kredit")


async def get_credit(telegram_id: int) -> int:
    db = await get_db()
    async with db.execute("SELECT kredit FROM users WHERE telegram_id = ?", (telegram_id,)) as cur:
        row = await cur.fetchone()
    return row["kredit"] if row else 0


async def deduct_credit(telegram_id: int) -> bool:
    db = await get_db()
    async with db.execute("SELECT kredit FROM users WHERE telegram_id = ?", (telegram_id,)) as cur:
        row = await cur.fetchone()
    if not row or row["kredit"] < 1:
        return False
    await db.execute("UPDATE users SET kredit = kredit - 1 WHERE telegram_id = ?", (telegram_id,))
    await db.commit()
    return True


async def add_credit(telegram_id: int, jumlah: int):
    db = await get_db()
    await db.execute("UPDATE users SET kredit = kredit + ? WHERE telegram_id = ?", (jumlah, telegram_id))
    await db.commit()
