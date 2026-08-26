"""Validatsiya ssylok i opredelenie platformy-istochnika video."""

import re
from typing import Optional
from urllib.parse import urlparse

# Ishchet pervyy http(s) URL v proizvolnom tekste soobshcheniya.
URL_REGEX = re.compile(r"(https?://\S+)", re.IGNORECASE)

# Klyuchevye slova domenov dlya opredeleniya platformy.
PLATFORM_PATTERNS = {
    "youtube": re.compile(r"(youtube\.com|youtu\.be)", re.IGNORECASE),
    "tiktok": re.compile(r"tiktok\.com", re.IGNORECASE),
    "instagram": re.compile(r"instagram\.com", re.IGNORECASE),
    "pinterest": re.compile(r"(pinterest\.[a-z.]+|pin\.it)", re.IGNORECASE),
    "twitter": re.compile(r"(twitter\.com|x\.com)", re.IGNORECASE),
    "facebook": re.compile(r"(facebook\.com|fb\.watch)", re.IGNORECASE),
}

PLATFORM_LABELS = {
    "youtube": "YouTube",
    "tiktok": "TikTok",
    "instagram": "Instagram",
    "pinterest": "Pinterest",
    "twitter": "Twitter/X",
    "facebook": "Facebook",
    "other": "drugaya platforma (cherez yt-dlp)",
}


def extract_url(text: str) -> Optional[str]:
    """Vozvrashchaet pervuyu ssylku iz teksta soobshcheniya, esli ona est."""
    if not text:
        return None
    match = URL_REGEX.search(text)
    if not match:
        return None
    # Ubiraem sluchaynye zavershayushchie znaki prepinaniya/skobki.
    url = match.group(1).rstrip(").,!?;>\"'")
    return url


def is_supported(url: str) -> bool:
    """Bazovaya proverka, chto stroka pohozha na korrektnyy http(s) URL."""
    try:
        result = urlparse(url)
        return result.scheme in ("http", "https") and bool(result.netloc)
    except ValueError:
        return False


def detect_platform(url: str) -> str:
    """Opredelyaet platformu po domenu ssylki. 'other' - esli ne raspoznano
    (yt-dlp mozhet vsyo ravno eyo podderzhivat)."""
    for platform, pattern in PLATFORM_PATTERNS.items():
        if pattern.search(url):
            return platform
    return "other"
