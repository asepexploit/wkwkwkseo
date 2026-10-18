import asyncio as _asyncio
import io
import logging
import re

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import ContextTypes

from app.bot.middlewares.auth import ensure_registered
from app.bot.middlewares.banned import is_banned
from app.bot.middlewares.rate_limit import is_rate_limited, is_processing, set_processing
from app.services.credit_service import get_credit, deduct_credit
from app.services.telegraph_service import create_telegraph_page
from app.utils.validator import is_valid_domain, clean_domain
from app.utils.formatter import format_result
from app.utils.constants import ADMIN_ID

logger = logging.getLogger(__name__)


def _compress_screenshot(data: bytes, max_width: int = 1280, quality: int = 82) -> bytes:
    try:
        from PIL import Image, ImageDraw, ImageFont

        base = Image.open(io.BytesIO(data)).convert("RGBA")
        if base.width > max_width:
            ratio = max_width / base.width
            base = base.resize((max_width, int(base.height * ratio)), Image.LANCZOS)

        w, h = base.size
        short = min(w, h)
        font_size = max(16, int(short * 0.032))
        margin = max(12, int(short * 0.025))

        # Coba font sistem Windows, fallback default
        _font_candidates = [
            r"C:\Windows\Fonts\arialbd.ttf",
            r"C:\Windows\Fonts\arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
        font = None
        for fp in _font_candidates:
            try:
                font = ImageFont.truetype(fp, font_size)
                break
            except Exception:
                pass
        if font is None:
            font = ImageFont.load_default()

        text = "@wkwkwkseo_bot"
        overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        x, y = w - margin, h - margin
        off = max(1, font_size // 16)

        # Shadow
        draw.text((x + off, y + off), text, font=font,
                  fill=(0, 0, 0, 90), anchor="rd")
        # Teks utama putih + outline hitam tipis
        draw.text((x, y), text, font=font, anchor="rd",
                  fill=(255, 255, 255, 200),
                  stroke_width=max(1, font_size // 14),
                  stroke_fill=(0, 0, 0, 160))

        out = Image.alpha_composite(base, overlay).convert("RGB")
        buf = io.BytesIO()
        out.save(buf, format="JPEG", quality=quality, optimize=True)
        return buf.getvalue()
    except Exception:
        return data


_LOADING_SUFFIX = "\n<i>Proses ini membutuhkan waktu 30 detik - 1 menit.</i>"
_frames = [
    "🔍 Mengecek <code>{}</code>..." + _LOADING_SUFFIX,
    "🌐 Mengecek <code>{}</code>..." + _LOADING_SUFFIX,
    "📊 Mengecek <code>{}</code>..." + _LOADING_SUFFIX,
    "🔎 Mengecek <code>{}</code>..." + _LOADING_SUFFIX,
]


async def check_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id

    if await is_banned(update):
        await update.message.reply_text("Akun kamu dibanned.")
        return

    if is_rate_limited(tg_id):
        await update.message.reply_text("Terlalu banyak request. Tunggu sebentar.")
        return

    if is_processing(tg_id):
        await update.message.reply_text(
            "⏳ <b>Sedang diproses...</b>\n\n"
            "Permintaan sebelumnya belum selesai.\n"
            "Tunggu hingga hasil muncul, lalu kirim domain baru.",
            parse_mode="HTML",
        )
        return

    await ensure_registered(update)

    text = update.message.text.strip()

    # Support multi-domain: pisahkan per baris/spasi/koma
    raw_lines = re.split(r"[\n,\s]+", text)
    domains = []
    invalid = []
    for raw in raw_lines:
        raw = raw.strip()
        if not raw:
            continue
        if is_valid_domain(raw):
            d = clean_domain(raw)
            if d not in domains:
                domains.append(d)
        else:
            invalid.append(raw)

    if not domains:
        await update.message.reply_text(
            "Format domain salah.\nContoh yang benar:\n"
            "<code>example.com</code>\n"
            "<code>google.com\ntokopedia.com</code>",
            parse_mode="HTML",
        )
        return

    if len(domains) > 20:
        await update.message.reply_text(
            f"Maksimal 20 domain sekaligus. Kamu mengirim {len(domains)} domain.",
            parse_mode="HTML",
        )
        return

    if invalid:
        await update.message.reply_text(
            f"Domain tidak valid diabaikan: {', '.join(f'<code>{d}</code>' for d in invalid)}",
            parse_mode="HTML",
        )

    is_admin = tg_id == ADMIN_ID
    if not is_admin and len(domains) > 1:
        kredit = await get_credit(tg_id)
        if kredit < len(domains):
            await update.message.reply_text(
                f"❌ Kredit tidak cukup.\n\n"
                f"Domain dikirim : <b>{len(domains)}</b>\n"
                f"Kredit kamu   : <b>{kredit}</b>\n\n"
                f"Kurangi jumlah domain atau /topup terlebih dahulu.",
                parse_mode="HTML",
            )
            return

    if len(domains) == 1:
        await _do_check(update.message, ctx, domains[0], force_refresh=False, tg_id=tg_id)
    else:
        await _do_check_multi(update.message, ctx, domains, tg_id=tg_id)


async def refresh_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Handler untuk tombol 'Cek Sekarang' (paksa refresh cache)."""
    query = update.callback_query
    await query.answer()
    tg_id = query.from_user.id
    domain = query.data.replace("refresh_", "", 1)

    kredit = await get_credit(tg_id)
    is_admin = tg_id == ADMIN_ID
    if kredit < 1 and not is_admin:
        await query.message.reply_text("Kredit kamu habis. Ketik /topup untuk isi ulang.")
        return

    await query.message.edit_reply_markup(reply_markup=None)
    await _do_check(query.message, ctx, domain, force_refresh=True, tg_id=tg_id)


async def _do_check(message, ctx, domain: str, force_refresh: bool, tg_id: int | None = None):
    if tg_id is None:
        tg_id = message.chat.id

    is_admin = tg_id == ADMIN_ID
    kredit = await get_credit(tg_id)
    if kredit < 1 and not is_admin:
        await message.reply_text("Kredit kamu habis. Ketik /topup untuk isi ulang.")
        return

    set_processing(tg_id, True)
    try:
        msg_loading = await message.reply_text(
            _frames[0].format(domain), parse_mode="HTML"
        )

        queue_manager = ctx.bot_data.get("queue_manager")

        if force_refresh:
            from app.services.domain_service import delete_cache
            await delete_cache(domain)

        enqueue_task = _asyncio.create_task(queue_manager.enqueue(domain, tg_id=tg_id))

        frame_idx = 0
        while not enqueue_task.done():
            await _asyncio.sleep(3)
            if enqueue_task.done():
                break
            frame_idx = (frame_idx + 1) % len(_frames)
            antrian = queue_manager.queue_size()
            aktif = queue_manager.active_count()
            try:
                if antrian > 0:
                    await msg_loading.edit_text(
                        f"⏳ <b>Menunggu antrian...</b>\n\n"
                        f"Domain kamu: <code>{domain}</code>\n"
                        f"Sedang diproses: <b>{aktif}</b> domain\n"
                        f"Antrian di depan kamu: <b>{antrian}</b> domain\n\n"
                        f"<i>Sabar ya, sebentar lagi giliranmu! 😊</i>",
                        parse_mode="HTML",
                    )
                else:
                    await msg_loading.edit_text(_frames[frame_idx].format(domain), parse_mode="HTML")
            except Exception:
                pass

        try:
            result = await enqueue_task
        except Exception as e:
            try:
                await msg_loading.delete()
            except Exception:
                pass
            logger.error(f"[check] gagal {domain}: {e}")
            await message.reply_text(
                f"❌ Gagal mengecek <code>{domain}</code>.\n"
                f"<i>Kredit tidak dipotong.</i>",
                parse_mode="HTML",
            )
            return

        try:
            await msg_loading.delete()
        except Exception:
            pass

        from_cache = result.get("from_cache", False)

        # Jika semua metrik None, anggap gagal
        if result.get("da") is None and result.get("dr") is None:
            await message.reply_text(
                f"❌ Tidak dapat mengambil data untuk <code>{domain}</code>.\n"
                f"<i>Kredit tidak dipotong.</i>",
                parse_mode="HTML",
            )
            return

        try:
            from app.services.log_service import log_cek
            username = getattr(message.from_user, "username", None) if hasattr(message, "from_user") else None
            await log_cek(tg_id, username, domain, result, from_cache)
        except Exception as _le:
            logger.warning(f"log_cek error: {_le}")

        if not is_admin and not from_cache:
            await deduct_credit(tg_id)
        kredit_sisa = await get_credit(tg_id)

        msg = format_result(
            domain,
            result["da"], result["pa"], result["ss"], result["age"],
            result["dr"], result["bc"], result.get("bc_df"), result["rd"], result.get("rd_df"),
            kredit_sisa,
            from_cache=from_cache,
            cached_at=result.get("cached_at"),
        )

        try:
            detail_url = await create_telegraph_page(
                domain,
                result["da"], result["pa"], result["ss"], result["age"],
                result["dr"], result["bc"], result.get("bc_df"), result["rd"], result.get("rd_df"),
                result.get("backlinks", []),
            )
            msg += f"\n\n<a href='{detail_url}'>📊 Lihat Backlink</a>"
        except Exception as e:
            logger.error(f"Telegraph error: {e}")

        reply_markup = None
        if from_cache:
            reply_markup = InlineKeyboardMarkup([[
                InlineKeyboardButton("🔄 Cek Sekarang (-1 kredit)", callback_data=f"refresh_{domain}")
            ]])

        screenshot: bytes | None = result.get("screenshot")
        if screenshot:
            loop = _asyncio.get_event_loop()
            screenshot = await loop.run_in_executor(None, _compress_screenshot, screenshot)
            sent = False
            for attempt in range(3):
                try:
                    await message.reply_photo(
                        photo=io.BytesIO(screenshot),
                        caption=msg,
                        parse_mode="HTML",
                        reply_markup=reply_markup,
                    )
                    sent = True
                    break
                except Exception as e:
                    logger.warning(f"reply_photo attempt {attempt+1} gagal: {e}")
                    if attempt < 2:
                        await _asyncio.sleep(2)
            if not sent:
                await message.reply_text(
                    msg, parse_mode="HTML",
                    disable_web_page_preview=False,
                    reply_markup=reply_markup,
                )
        else:
            await message.reply_text(
                msg, parse_mode="HTML",
                disable_web_page_preview=False,
                reply_markup=reply_markup,
            )
    finally:
        set_processing(tg_id, False)


_MULTI_PAGE_SIZE = 5  # domain per halaman


def _build_multi_page(entries: list[dict], page: int, total_pages: int, kredit: int) -> tuple[str, InlineKeyboardMarkup | None]:
    """Build pesan 1 halaman untuk multi-domain result."""
    total_entries = entries  # passed as current page slice, total count from caller
    lines = []

    # Header
    pg = f"  <i>hal {page+1}/{total_pages}</i>" if total_pages > 1 else ""
    lines.append(f"<b>wkwkwkseo</b>{pg}")
    lines.append("<i>ℹ️ Cek massal tidak menyertakan screenshot Ahrefs.</i>")
    lines.append("<i>Cek 1 domain untuk mendapatkan screenshot.</i>")
    lines.append("")

    for i, entry in enumerate(entries):
        domain = entry["domain"]
        num = page * _MULTI_PAGE_SIZE + i + 1
        if entry.get("error"):
            err = entry.get("err_msg", "Gagal dicek")
            lines.append(f"<b>{num}.</b> <code>{domain}</code>")
            lines.append(f"     ❌ {err}")
            lines.append(f"     <i>Kredit tidak dipotong</i>")
        else:
            r = entry["result"]
            da  = r.get("da",  "—")
            pa  = r.get("pa",  "—")
            dr  = r.get("dr",  "—")
            bc  = r.get("bc",  "—")
            rd  = r.get("rd",  "—")
            ss  = r.get("ss",  "—")
            age = r.get("age", "—")
            from_cache = r.get("from_cache", False)
            src = "📦" if from_cache else "🔍"
            lines.append(f"<b>{num}.</b> <code>{domain}</code> {src}")
            bc_df = r.get("bc_df")
            rd_df = r.get("rd_df")
            bc_df = r.get("bc_df")
            rd_df = r.get("rd_df")
            lines.append(f"     DA <b>{da}</b>  PA <b>{pa}</b>  SS <b>{ss}</b>")
            lines.append(f"     DR <b>{dr}</b>")
            if bc_df is not None:
                lines.append(f"     BC <b>{bc}</b> <i>({bc_df}% dofollow)</i>")
                lines.append(f"     RD <b>{rd}</b> <i>({rd_df}% dofollow)</i>" if rd_df is not None else f"     RD <b>{rd}</b>")
            else:
                lines.append(f"     BC <b>{bc}</b>  RD <b>{rd}</b>")
            lines.append(f"     Age <b>{age}</b>")
            if from_cache:
                from app.utils.formatter import _fmt_tanggal_wib
                tgl = _fmt_tanggal_wib(r.get("cached_at"))
                lines.append(f"     <i>📦 Cache · {tgl}</i>")
            else:
                lines.append(f"     <i>🔍 Data baru dicek</i>")
        if i < len(entries) - 1:
            lines.append("")

    lines.append("")
    lines.append(f"<code>{'─' * 24}</code>")
    lines.append(f"💳 Kredit: <b>{kredit}</b>   📦 cache  🔍 baru")

    text = "\n".join(lines)

    # Pagination buttons
    markup = None
    if total_pages > 1:
        btns = []
        if page > 0:
            btns.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"multipage_prev_{page}"))
        if page < total_pages - 1:
            btns.append(InlineKeyboardButton("Next ➡️", callback_data=f"multipage_next_{page}"))
        if btns:
            markup = InlineKeyboardMarkup([btns])
    return text, markup


async def _do_check_multi(message, ctx, domains: list[str], tg_id: int):
    """Cek banyak domain sekaligus secara paralel, hasil digabung jadi 1 pesan dengan pagination."""
    is_admin = tg_id == ADMIN_ID
    queue_manager = ctx.bot_data.get("queue_manager")

    set_processing(tg_id, True)
    try:
        domain_list = "\n".join(f"  • <code>{d}</code>" for d in domains)
        msg_loading = await message.reply_text(
            f"🔍 Mengecek <b>{len(domains)} domain</b> secara paralel...\n"
            f"{domain_list}\n\n"
            f"<i>Screenshot Ahrefs tidak tersedia untuk cek massal.</i>\n"
            f"<i>Proses membutuhkan waktu 30 detik - 1 menit.</i>",
            parse_mode="HTML",
        )

        tasks = [
            _asyncio.create_task(queue_manager.enqueue(d, tg_id=tg_id))
            for d in domains
        ]

        _mf = ["🔍", "🌐", "📊", "🔎"]
        fi = 0
        while not all(t.done() for t in tasks):
            await _asyncio.sleep(3)
            if all(t.done() for t in tasks):
                break
            fi = (fi + 1) % len(_mf)
            done_n = sum(1 for t in tasks if t.done())
            antrian = queue_manager.queue_size()
            aktif = queue_manager.active_count()
            try:
                if antrian > 0 and done_n == 0:
                    await msg_loading.edit_text(
                        f"⏳ <b>Menunggu antrian...</b>\n\n"
                        f"Domain kamu: <b>{len(domains)} domain</b>\n"
                        f"Sedang diproses: <b>{aktif}</b> domain (user lain)\n"
                        f"Antrian di depan kamu: <b>{antrian - len(domains)}</b> domain\n\n"
                        f"<i>Sabar ya, sebentar lagi giliranmu! 😊</i>",
                        parse_mode="HTML",
                    )
                else:
                    await msg_loading.edit_text(
                        f"{_mf[fi]} Mengecek <b>{len(domains)} domain</b>... <b>{done_n}/{len(domains)}</b> selesai\n"
                        f"{domain_list}\n\n"
                        f"<i>Screenshot Ahrefs tidak tersedia untuk cek massal.</i>\n"
                        f"<i>Proses membutuhkan waktu 30 detik - 1 menit.</i>",
                        parse_mode="HTML",
                    )
            except Exception:
                pass

        raw_results = await _asyncio.gather(*tasks, return_exceptions=True)

        try:
            await msg_loading.delete()
        except Exception:
            pass

        entries = []
        for domain, result in zip(domains, raw_results):
            if isinstance(result, Exception):
                entries.append({"domain": domain, "error": True, "result": {}, "err_msg": str(result)})
                continue
            # Anggap gagal jika semua metrik None
            if result.get("da") is None and result.get("dr") is None:
                entries.append({"domain": domain, "error": True, "result": {}, "err_msg": "Data tidak tersedia"})
                continue
            from_cache = result.get("from_cache", False)
            if not is_admin and not from_cache:
                await deduct_credit(tg_id)
            try:
                from app.services.log_service import log_cek
                username = getattr(message.from_user, "username", None) if hasattr(message, "from_user") else None
                await log_cek(tg_id, username, domain, result, from_cache)
            except Exception:
                pass
            entries.append({"domain": domain, "error": False, "result": result})

        kredit_sisa = await get_credit(tg_id)
        total_pages = max(1, (len(entries) + _MULTI_PAGE_SIZE - 1) // _MULTI_PAGE_SIZE)

        page_key = f"multi_{tg_id}_{message.message_id}"
        ctx.bot_data[page_key] = {"entries": entries, "kredit": kredit_sisa, "total_pages": total_pages}

        page_entries = entries[:_MULTI_PAGE_SIZE]
        text, markup = _build_multi_page(page_entries, 0, total_pages, kredit_sisa)
        sent = await message.reply_text(text, parse_mode="HTML", disable_web_page_preview=True, reply_markup=markup)

        if total_pages > 1:
            ctx.bot_data[page_key]["msg_id"] = sent.message_id
            ctx.bot_data[page_key]["chat_id"] = message.chat.id
    finally:
        set_processing(tg_id, False)


async def multipage_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Handler tombol Next/Prev untuk hasil multi-domain."""
    query = update.callback_query
    await query.answer()
    tg_id = query.from_user.id
    data = query.data  # multipage_prev_2 atau multipage_next_2

    parts = data.split("_")
    direction = parts[1]   # prev / next
    cur_page = int(parts[2])
    new_page = cur_page - 1 if direction == "prev" else cur_page + 1

    # Cari page_key di bot_data
    page_key = None
    for k in list(ctx.bot_data.keys()):
        if k.startswith(f"multi_{tg_id}_"):
            page_key = k
            break

    if not page_key or page_key not in ctx.bot_data:
        await query.edit_message_reply_markup(reply_markup=None)
        return

    data_store = ctx.bot_data[page_key]
    entries = data_store["entries"]
    kredit = data_store["kredit"]
    total_pages = data_store["total_pages"]

    start = new_page * _MULTI_PAGE_SIZE
    page_entries = entries[start:start + _MULTI_PAGE_SIZE]
    text, markup = _build_multi_page(page_entries, new_page, total_pages, kredit)
    await query.edit_message_text(text, parse_mode="HTML", disable_web_page_preview=True, reply_markup=markup)
