"""Zagruzka video/audio cherez yt-dlp v otdelnom potoke (ne blokiruet asyncio)."""

import asyncio
import logging
import os
import uuid
from dataclasses import dataclass
from typing import Optional

import yt_dlp

from config import TEMP_DIR

logger = logging.getLogger(__name__)


class DownloadError(Exception):
    """Vyzyvaetsya pri lyuboy oshibke polucheniya informatsii ili zagruzki media."""


@dataclass
class DownloadResult:
    filepath: str
    filesize: int
    title: str
    ext: str


def _safe_title(title: str) -> str:
    """Ubiraet simvoly, nedopustimye v imenah faylov."""
    cleaned = re.sub(r'[\\/*?:"<>|]', "_", title).strip()
    return cleaned[:150] or "file"


def _video_format_string(quality: Optional[str]) -> str:
    quality_map = {
        "360": "bestvideo[height<=360]+bestaudio/best[height<=360]",
        "720": "bestvideo[height<=720]+bestaudio/best[height<=720]",
        "1080": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
        "best": "bestvideo+bestaudio/best",
    }
    return quality_map.get(quality or "best", "bestvideo+bestaudio/best")


def _sync_download(url: str, content_type: str, quality: Optional[str], job_id: str) -> DownloadResult:
    """Sinhronnaya (blokiruyushchaya) zagruzka cherez yt-dlp. Zapuskaetsya v executor."""
    os.makedirs(TEMP_DIR, exist_ok=True)
    output_template = os.path.join(TEMP_DIR, f"{job_id}.%(ext)s")

    ydl_opts = {
        "outtmpl": output_template,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "restrictfilenames": True,
    }

    if content_type == "audio":
        bitrate = quality or "192"
        ydl_opts.update(
            {
                "format": "bestaudio/best",
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": bitrate,
                    }
                ],
            }
        )
    else:
        ydl_opts["format"] = _video_format_string(quality)
        ydl_opts["merge_output_format"] = "mp4"

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            raw_path = ydl.prepare_filename(info)
            base, _ = os.path.splitext(raw_path)

            if content_type == "audio":
                filepath = f"{base}.mp3"
            else:
                mp4_path = f"{base}.mp4"
                filepath = mp4_path if os.path.exists(mp4_path) else raw_path

            if not os.path.exists(filepath):
                raise DownloadError("Fayl ne nayden posle zagruzki")

            filesize = os.path.getsize(filepath)
            title = info.get("title") or "file"
            ext = os.path.splitext(filepath)[1].lstrip(".")
            return DownloadResult(filepath=filepath, filesize=filesize, title=_safe_title(title), ext=ext)
    except yt_dlp.utils.DownloadError as exc:
        raise DownloadError(str(exc)) from exc
    except DownloadError:
        raise
    except Exception as exc:  # noqa: BLE001 - khotim perehvatit lyubuyu oshibku yt-dlp/ffmpeg
        logger.exception("Unexpected error during download")
        raise DownloadError(str(exc)) from exc


def _sync_extract_info(url: str) -> dict:
    ydl_opts = {"quiet": True, "no_warnings": True, "skip_download": True, "noplaylist": True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return {"title": info.get("title") or "Bez nazvaniya", "duration": info.get("duration")}
    except yt_dlp.utils.DownloadError as exc:
        raise DownloadError(str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected error while fetching info")
        raise DownloadError(str(exc)) from exc


async def get_video_info(url: str) -> dict:
    """Poluchaet metadannye (nazvanie, dlitelnost) bez zagruzki fayla."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _sync_extract_info, url)


async def download_media(url: str, content_type: str, quality: Optional[str]) -> DownloadResult:
    """Asinhronno zapuskaet zagruzku v otdelnom potoke, chtoby ne blokirovat event loop."""
    job_id = uuid.uuid4().hex
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _sync_download, url, content_type, quality, job_id)


def cleanup_file(filepath: Optional[str]) -> None:
    """Udalyaet vremennyy fayl posle otpravki ili pri oshibke."""
    if not filepath:
        return
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
    except OSError:
        logger.warning("Ne udalos udalit vremennyy fayl: %s", filepath)
