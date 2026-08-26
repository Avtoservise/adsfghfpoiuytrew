"""Obrabotchiki Telegram-bota: komandy, ssylki, inline-knopki."""

import logging
import uuid

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InputFile, Update
from telegram.ext import ContextTypes

from config import MAX_TELEGRAM_FILE_SIZE
from utils.downloader import DownloadError, cleanup_file, download_media, get_video_info
from utils.validator import PLATFORM_LABELS, detect_platform, extract_url, is_supported

logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Obrabotchik komandy /start."""
    await update.message.reply_text(
        "Privet! Otprav mne ssylku na video, i ya skachayu ego.\n\n"
        "Podderzhivayutsya YouTube, TikTok, Instagram, Pinterest, Twitter/X, Facebook i drugie sayty "
        "(cherez yt-dlp)."
    )


async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Lovit tekstovoe soobshchenie so ssylkoy, opredelyaet platformu i pokazyvaet menyu vybora."""
    text = update.message.text or ""
    url = extract_url(text)

    if not url or not is_supported(url):
        await update.message.reply_text(
            "❌ Ne nashyol v soobshchenii korrektnuyu ssylku. Prishlite, pozhaluysta, pryamuyu ssylku na video."
        )
        return

    platform = detect_platform(url)
    status_msg = await update.message.reply_text("🔍 Proveryayu ssylku...")

    try:
        info = await get_video_info(url)
    except DownloadError:
        await status_msg.edit_text(
            "❌ Ne udalos poluchit video. Vozmozhno, ssylka nedostupna, video zashchishcheno ili region zablokirovan."
        )
        return

    job_id = uuid.uuid4().hex[:8]
    jobs = context.user_data.setdefault("jobs", {})
    jobs[job_id] = {"url": url, "title": info["title"]}

    keyboard = [
        [
            InlineKeyboardButton("🎥 Video (MP4)", callback_data=f"type:video:{job_id}"),
            InlineKeyboardButton("🎵 Audio (MP3)", callback_data=f"type:audio:{job_id}"),
        ]
    ]
    await status_msg.edit_text(
        f"🔍 Nashyol video: {info['title']}\n"
        f"Platforma: {PLATFORM_LABELS.get(platform, platform)}\n\n"
        "Vyberite format:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def handle_type_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Obrabatyvaet vybor tipa kontenta (video/audio) i pokazyvaet vybor kachestva."""
    query = update.callback_query
    await query.answer()
    _, content_type, job_id = query.data.split(":")

    jobs = context.user_data.get("jobs", {})
    job = jobs.get(job_id)
    if not job:
        await query.edit_message_text("⚠️ Zapros ustarel, prishlite ssylku zanovo.")
        return

    job["content_type"] = content_type

    if content_type == "video":
        keyboard = [
            [
                InlineKeyboardButton("360p", callback_data=f"quality:360:{job_id}"),
                InlineKeyboardButton("720p", callback_data=f"quality:720:{job_id}"),
                InlineKeyboardButton("1080p", callback_data=f"quality:1080:{job_id}"),
                InlineKeyboardButton("Best", callback_data=f"quality:best:{job_id}"),
            ]
        ]
        await query.edit_message_text("Vyberite kachestvo video:", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        keyboard = [
            [
                InlineKeyboardButton("128 kbps", callback_data=f"quality:128:{job_id}"),
                InlineKeyboardButton("320 kbps", callback_data=f"quality:320:{job_id}"),
            ]
        ]
        await query.edit_message_text("Vyberite bitreyt audio:", reply_markup=InlineKeyboardMarkup(keyboard))


async def handle_quality_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Zapuskaet zagruzku posle vybora kachestva i otpravlyaet gotovyy fayl."""
    query = update.callback_query
    await query.answer()
    _, quality, job_id = query.data.split(":")

    jobs = context.user_data.get("jobs", {})
    job = jobs.get(job_id)
    if not job:
        await query.edit_message_text("⚠️ Zapros ustarel, prishlite ssylku zanovo.")
        return

    url = job["url"]
    content_type = job["content_type"]

    await query.edit_message_text("⏳ Idyot zagruzka, podozhdite...")

    filepath = None
    try:
        result = await download_media(url, content_type, quality)
        filepath = result.filepath

        if result.filesize > MAX_TELEGRAM_FILE_SIZE:
            await query.edit_message_text(
                "❌ Fayl slishkom bolshoy dlya otpravki cherez Telegram (limit ~50 MB dlya standartnogo Bot API). "
                "Poprobuyte vybrat bolee nizkoe kachestvo."
            )
            return

        await query.edit_message_text("✅ Gotovo! Otpravlyayu fayl...")
        with open(filepath, "rb") as file_obj:
            await context.bot.send_document(
                chat_id=query.message.chat_id,
                document=InputFile(file_obj, filename=f"{result.title}.{result.ext}"),
            )
    except DownloadError as exc:
        logger.warning("Download failed for %s: %s", url, exc)
        await query.edit_message_text(
            "❌ Ne udalos skachat video. Vozmozhno, ssylka nedostupna ili video zashchishcheno."
        )
    except Exception:  # noqa: BLE001 - lyubaya neozhidannaya oshibka pri otpravke
        logger.exception("Unexpected error while sending file")
        await query.edit_message_text("❌ Proizoshla nepredvidennaya oshibka pri otpravke fayla.")
    finally:
        cleanup_file(filepath)
        jobs.pop(job_id, None)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Globalnyy obrabotchik neperehvachennyh oshibok."""
    logger.error("Exception while handling update: %s", update, exc_info=context.error)
