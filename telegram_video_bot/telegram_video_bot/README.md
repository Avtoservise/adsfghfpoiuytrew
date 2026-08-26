# Telegram Video Downloader Bot

Telegram-бот на `python-telegram-bot` 20.x, который принимает ссылки на видео (YouTube, TikTok, Instagram, Pinterest, Twitter/X, Facebook и др.), даёт выбрать формат/качество через inline-кнопки и отправляет готовый файл в чат как документ.

## Структура проекта

```
telegram_video_bot/
├── bot.py                 # Точка входа: создание Application и запуск polling
├── config.py              # Загрузка настроек из .env
├── handlers.py            # /start, обработка ссылок, inline-кнопки
├── utils/
│   ├── validator.py       # Распознавание ссылок и определение платформы
│   └── downloader.py      # Асинхронная обёртка над yt-dlp
├── requirements.txt
├── .env.example
└── README.md
```

## Установка

1. **Python 3.10+** и **FFmpeg** должны быть установлены на сервере:
   ```bash
   # Ubuntu/Debian
   sudo apt update && sudo apt install -y ffmpeg

   # macOS (Homebrew)
   brew install ffmpeg
   ```

2. Создайте виртуальное окружение и установите зависимости:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Скопируйте `.env.example` в `.env` и вставьте токен бота, полученный от [@BotFather](https://t.me/BotFather):
   ```bash
   cp .env.example .env
   # отредактируйте BOT_TOKEN=...
   ```

4. Запустите бота:
   ```bash
   python bot.py
   ```

## Как это работает

1. Пользователь присылает ссылку → `handlers.handle_link` извлекает URL (`utils.validator.extract_url`), проверяет его и определяет платформу (`detect_platform`).
2. Бот запрашивает у yt-dlp только метаданные (без загрузки) и показывает название видео и кнопки выбора типа (Видео/Аудио).
3. После выбора типа показываются кнопки качества/битрейта.
4. После выбора качества запускается реальная загрузка (`utils.downloader.download_media`) в отдельном потоке через `loop.run_in_executor`, чтобы не блокировать event loop и других пользователей.
5. Готовый файл отправляется через `send_document` (без сжатия Telegram), затем временный файл немедленно удаляется (`finally` блок в `handle_quality_choice`).
6. Если файл превышает `MAX_TELEGRAM_FILE_SIZE` (по умолчанию 50 МБ — лимит стандартного Bot API), бот сообщает об ошибке после фактической загрузки — без предварительных ограничений выбора.

## Важные замечания

- **Лимит размера файла:** стандартный Bot API позволяет ботам отправлять файлы до 50 МБ. Для больших файлов нужен собственный [Local Bot API Server](https://github.com/tdlib/telegram-bot-api) (до 2000 МБ) — в этом случае поднимите `MAX_TELEGRAM_FILE_SIZE` в `.env` и укажите `base_url` локального сервера в `Application.builder()`.
- **Instagram/Facebook часто требуют авторизацию:** для приватных/возрастных ограниченных видео yt-dlp может потребовать файл `cookies.txt` (опция `cookiefile` в `ydl_opts`).
- **Региональные блокировки и защита:** отлавливаются как `DownloadError` и превращаются в понятное сообщение пользователю.
- **Очередь запросов:** активные запросы хранятся в `context.user_data["jobs"]` по короткому `job_id`, чтобы разные пользователи могли одновременно выбирать формат/качество без конфликтов.
- **Масштабирование:** для высокой нагрузки рассмотрите ограничение числа одновременных загрузок через `asyncio.Semaphore` вокруг `download_media`.
