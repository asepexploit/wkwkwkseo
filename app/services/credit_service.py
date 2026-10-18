from app.database.connection import get_db


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
