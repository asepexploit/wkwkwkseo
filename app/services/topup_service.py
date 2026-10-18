from app.database.connection import get_db
from app.models.transaction import Transaction
from app.utils.constants import PAKET


async def create_transaction(telegram_id: int, paket_key: str, bukti_url: str) -> Transaction:
    db = await get_db()
    paket = PAKET[paket_key]
    async with db.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,)) as cur:
        row = await cur.fetchone()
    user_id = row["id"]

    await db.execute(
        "INSERT INTO transactions (user_id, paket, jumlah_kredit, harga, bukti_url) VALUES (?,?,?,?,?)",
        (user_id, paket_key, paket["kredit"], paket["harga"], bukti_url),
    )
    await db.commit()
    async with db.execute("SELECT * FROM transactions WHERE user_id = ? ORDER BY id DESC LIMIT 1", (user_id,)) as cur:
        row = await cur.fetchone()
    return Transaction.from_row(row)


async def get_pending_transactions() -> list[Transaction]:
    db = await get_db()
    async with db.execute("SELECT * FROM transactions WHERE status = 'pending' ORDER BY created_at") as cur:
        rows = await cur.fetchall()
    return [Transaction.from_row(r) for r in rows]


async def confirm_transaction(tx_id: int) -> Transaction | None:
    db = await get_db()
    await db.execute(
        "UPDATE transactions SET status='confirmed', confirmed_at=datetime('now') WHERE id=?", (tx_id,)
    )
    await db.commit()
    async with db.execute("SELECT * FROM transactions WHERE id = ?", (tx_id,)) as cur:
        row = await cur.fetchone()
    return Transaction.from_row(row) if row else None


async def reject_transaction(tx_id: int) -> Transaction | None:
    db = await get_db()
    await db.execute("UPDATE transactions SET status='rejected' WHERE id=?", (tx_id,))
    await db.commit()
    async with db.execute("SELECT * FROM transactions WHERE id = ?", (tx_id,)) as cur:
        row = await cur.fetchone()
    return Transaction.from_row(row) if row else None
