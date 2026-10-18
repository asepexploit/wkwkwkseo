from telegram import Update
from telegram.ext import ContextTypes

from app.services.topup_service import confirm_transaction, reject_transaction, get_pending_transactions
from app.services.credit_service import add_credit
from app.services.user_service import get_user, set_banned
from app.database.connection import get_db
from app.utils.constants import ADMIN_ID, PAKET


def _is_admin(update: Update) -> bool:
    return update.effective_user.id == ADMIN_ID


async def admin_konfirmasi(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update):
        return
    if not ctx.args:
        await update.message.reply_text("Usage: /admin_konfirmasi [tx_id]")
        return

    tx_id = int(ctx.args[0])
    tx = await confirm_transaction(tx_id)
    if not tx:
        await update.message.reply_text("Transaksi tidak ditemukan.")
        return

    db = await get_db()
    async with db.execute("SELECT telegram_id FROM users WHERE id = ?", (tx.user_id,)) as cur:
        row = await cur.fetchone()
    tg_id = row["telegram_id"]

    await add_credit(tg_id, tx.jumlah_kredit)
    await update.message.reply_text(f"✅ Transaksi {tx_id} dikonfirmasi. {tx.jumlah_kredit} kredit ditambahkan.")
    await ctx.bot.send_message(
        chat_id=tg_id,
        text=f"✅ Top up berhasil!\n{tx.jumlah_kredit} kredit masuk ke akunmu.",
    )


async def admin_reject(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update):
        return
    if not ctx.args:
        await update.message.reply_text("Usage: /admin_reject [tx_id]")
        return

    tx_id = int(ctx.args[0])
    tx = await reject_transaction(tx_id)
    if not tx:
        await update.message.reply_text("Transaksi tidak ditemukan.")
        return

    db = await get_db()
    async with db.execute("SELECT telegram_id FROM users WHERE id = ?", (tx.user_id,)) as cur:
        row = await cur.fetchone()
    tg_id = row["telegram_id"]

    await update.message.reply_text(f"❌ Transaksi {tx_id} direject.")
    await ctx.bot.send_message(
        chat_id=tg_id,
        text="❌ Top up kamu direject. Hubungi admin jika ada masalah.",
    )


async def admin_addkredit(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update):
        return
    if len(ctx.args) < 2:
        await update.message.reply_text("Usage: /admin_addkredit [telegram_id] [jumlah]")
        return
    tg_id = int(ctx.args[0])
    jumlah = int(ctx.args[1])
    await add_credit(tg_id, jumlah)
    await update.message.reply_text(f"✅ {jumlah} kredit ditambahkan ke user {tg_id}.")


async def admin_ban(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update):
        return
    if not ctx.args:
        await update.message.reply_text("Usage: /admin_ban [telegram_id]")
        return
    tg_id = int(ctx.args[0])
    await set_banned(tg_id, True)
    await update.message.reply_text(f"🚫 User {tg_id} dibanned.")


async def admin_stats(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update):
        return
    db = await get_db()

    async with db.execute("SELECT COUNT(*) as total FROM users") as cur:
        total_users = (await cur.fetchone())["total"]
    async with db.execute("SELECT COUNT(*) as total FROM users WHERE is_banned = 1") as cur:
        total_banned = (await cur.fetchone())["total"]
    async with db.execute("SELECT SUM(kredit) as total FROM users") as cur:
        total_kredit = (await cur.fetchone())["total"] or 0
    async with db.execute(
        "SELECT COUNT(*) as total FROM history_cek WHERE date(checked_at) = date('now')"
    ) as cur:
        cek_hari_ini = (await cur.fetchone())["total"]
    async with db.execute("SELECT COUNT(*) as total FROM history_cek") as cur:
        cek_total = (await cur.fetchone())["total"]
    async with db.execute("SELECT COUNT(*) as total FROM cache_domain") as cur:
        total_cache = (await cur.fetchone())["total"]
    async with db.execute("SELECT COUNT(*) as total FROM transactions WHERE status='pending'") as cur:
        pending = (await cur.fetchone())["total"]
    async with db.execute("SELECT COUNT(*) as total FROM transactions WHERE status='confirmed'") as cur:
        confirmed = (await cur.fetchone())["total"]
    async with db.execute("SELECT SUM(harga) as total FROM transactions WHERE status='confirmed'") as cur:
        total_omzet = (await cur.fetchone())["total"] or 0

    # Per paket
    paket_lines = []
    for paket_key in ["starter", "basic", "pro", "bulk"]:
        async with db.execute(
            "SELECT COUNT(*) as total FROM transactions WHERE status='confirmed' AND paket=?",
            (paket_key,)
        ) as cur:
            jml = (await cur.fetchone())["total"]
        paket_lines.append(f"  {paket_key.capitalize():<8}: {jml}x")

    msg = (
        "[ STATISTIK BOT ]\n"
        "\n"
        "— User —\n"
        f"  Total        : {total_users}\n"
        f"  Banned       : {total_banned}\n"
        f"  Total kredit : {total_kredit:,}\n"
        "\n"
        "— Cek Domain —\n"
        f"  Hari ini     : {cek_hari_ini}\n"
        f"  Total        : {cek_total:,}\n"
        f"  Cache        : {total_cache}\n"
        "\n"
        "— Topup —\n"
        f"  Pending      : {pending}\n"
        f"  Confirmed    : {confirmed}\n"
        f"  Omzet        : Rp{total_omzet:,}\n"
        "\n"
        "— Per Paket —\n"
        + "\n".join(paket_lines)
    )
    await update.message.reply_text(f"<pre>{msg}</pre>", parse_mode="HTML")


async def admin_broadcast(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update):
        return
    if not ctx.args:
        await update.message.reply_text(
            "Usage: /admin_broadcast [pesan]\n\nContoh:\n<code>/admin_broadcast Halo semua! Ada update baru nih.</code>",
            parse_mode="HTML"
        )
        return

    pesan = " ".join(ctx.args)
    db = await get_db()
    async with db.execute("SELECT telegram_id FROM users WHERE is_banned = 0 OR is_banned IS NULL") as cur:
        rows = await cur.fetchall()

    if not rows:
        await update.message.reply_text("Tidak ada user untuk dibroadcast.")
        return

    total = len(rows)
    berhasil = 0
    gagal = 0

    status_msg = await update.message.reply_text(f"📢 Memulai broadcast ke {total} user...")

    for row in rows:
        tg_id = row["telegram_id"]
        try:
            await ctx.bot.send_message(
                chat_id=tg_id,
                text=f"📢 <b>Pengumuman</b>\n\n{pesan}",
                parse_mode="HTML",
            )
            berhasil += 1
        except Exception:
            gagal += 1

    await status_msg.edit_text(
        f"📢 <b>Broadcast selesai</b>\n\n"
        f"  Total user : {total}\n"
        f"  Berhasil   : {berhasil}\n"
        f"  Gagal      : {gagal}",
        parse_mode="HTML",
    )


async def admin_pending(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update):
        return
    txs = await get_pending_transactions()
    if not txs:
        await update.message.reply_text("Tidak ada transaksi pending.")
        return

    lines = "\n".join(
        f"  [{tx.id}] {tx.paket} — Rp{tx.harga:,} — user_id:{tx.user_id}"
        for tx in txs
    )
    msg = (
        "╔══════════════════════╗\n"
        "║   📥 PENDING TOPUP   ║\n"
        "╚══════════════════════╝\n"
        "\n"
        f"{lines}"
    )
    await update.message.reply_text(f"<pre>{msg}</pre>", parse_mode="HTML")
