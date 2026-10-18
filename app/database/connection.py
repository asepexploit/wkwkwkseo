import aiosqlite
import os
from app.utils.constants import DB_PATH

_db: aiosqlite.Connection | None = None


async def get_db() -> aiosqlite.Connection:
    global _db
    if _db is None:
        _db = await aiosqlite.connect(DB_PATH)
        _db.row_factory = aiosqlite.Row
    return _db


async def init_db():
    db = await get_db()
    migrations_dir = os.path.join(os.path.dirname(__file__), "migrations")
    files = sorted(f for f in os.listdir(migrations_dir) if f.endswith(".sql"))
    for fname in files:
        path = os.path.join(migrations_dir, fname)
        with open(path, "r") as f:
            sql = f.read()
        await db.executescript(sql)
    await db.commit()
