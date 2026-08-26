import os
import logging

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError(
        "BOT_TOKEN ne zadan. Sozdayte fayl .env na osnove .env.example i ukazhite token bota."
    )

# Papka dlya vremennyh faylov (skachannye video/audio pered otpravkoy)
TEMP_DIR = os.getenv("TEMP_DIR", "downloads")

# Limit razmera fayla dlya otpravki cherez standartnyy Bot API (50 MB).
# Esli ispolzuetsya lokalnyy Bot API server, limit mozhno podnyat do 2000 MB.
MAX_TELEGRAM_FILE_SIZE = int(os.getenv("MAX_TELEGRAM_FILE_SIZE", 50 * 1024 * 1024))

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
)
