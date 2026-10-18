from app.database.connection import get_db
from app.models.user import User


async def get_or_create_user(telegram_id: int, username: str | None, nama: str | None) -> tuple[User, bool]:
    db = await get_db()
    async with db.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)) as cur:
        row = await cur.fetchone()
    if row:
        return User.from_row(row), False

    await db.execute(
        "INSERT INTO users (telegram_id, username, nama) VALUES (?, ?, ?)",
        (telegram_id, username, nama),
    )
    await db.commit()
    async with db.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)) as cur:
        row = await cur.fetchone()
    return User.from_row(row), True


async def get_user(telegram_id: int) -> User | None:
    db = await get_db()
    async with db.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)) as cur:
        row = await cur.fetchone()
    return User.from_row(row) if row else None


async def set_banned(telegram_id: int, banned: bool):
    db = await get_db()
    await db.execute("UPDATE users SET is_banned = ? WHERE telegram_id = ?", (int(banned), telegram_id))
    await db.commit()
