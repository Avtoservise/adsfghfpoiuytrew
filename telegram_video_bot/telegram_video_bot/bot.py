"""Tochka vhoda: sozdanie Application i zapusk bota (polling)."""

import logging

from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, filters

from config import BOT_TOKEN
from handlers import error_handler, handle_link, handle_quality_choice, handle_type_choice, start

logger = logging.getLogger(__name__)


def main() -> None:
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
    application.add_handler(CallbackQueryHandler(handle_type_choice, pattern=r"^type:"))
    application.add_handler(CallbackQueryHandler(handle_quality_choice, pattern=r"^quality:"))
    application.add_error_handler(error_handler)

    logger.info("Bot zapushchen, ozhidayu soobshcheniya...")
    application.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()
