# Telegram Video Subtitle Pipeline (Lab 2)

Реализация лабораторной работы №2 по оркестрации n8n: телеграм-бот принимает видео/ссылку, извлекает звук, распознаёт речь локальным Whisper, переводит текст через LLM и возвращает видео с русскими субтитрами.

## Архитектура
- **n8n** — основной оркестратор; workflow построен на Telegram Trigger, ветвлении по типу входа, обработке бинарных файлов и Execute Command.
- **PostgreSQL** — хранилище состояния n8n.
- **Traefik** — reverse-proxy и SSL termination для публичного доступа к n8n.
- **STT сервис (`pytorch-server`)** — FastAPI + `faster-whisper`, принимает аудио и возвращает SRT.
- **Внешние API** — OpenRouter (LLM для перевода), Telegram Bot API.
- Вспомогательные утилиты: `ffmpeg` (извлечение аудио, инкрустация субтитров).

Workflow (экспорт доступен через UI n8n):
1. `Telegram Trigger` (webhook) → Switch (видео файл / ссылка).
2. Ветка URL: HTTP Request скачивает файл; ветка файл: Telegram `getFile`.
3. Видео записывается в `/files/input-video.mp4`.
4. `Execute Command`: `ffmpeg` → `/files/audio.wav`.
5. `HTTP Request` на `pytorch-server` (`/transcribe`) — получаем английский SRT.
6. LangChain Chain + OpenRouter Qwen/Llama -> перевод EN→RU (строго SRT).
7. `Read/Write File` сохраняет `/files/out_ru.srt`.
8. `Execute Command`: `ffmpeg` добавляет субтитры → `/files/output_ru.mp4`.
9. `Telegram sendVideo` возвращает результат пользователю.

## Требования
- Docker 24+ и Docker Compose plugin.
- Домен с корректными DNS A/AAAA-записями для Traefik + открытые порты 80/443.
- Созданный Telegram бот и токен.
- Токен OpenRouter (или другой LLM, если переделать HTTP-ноду).
- Возможность скачать модель `Systran/faster-whisper-small` (≈1.5 ГБ).

## Подготовка окружения
1. **Клонирование**
   ```bash
   git clone https://github.com/cfaring/ssau-data-engineering-lab2.git
   cd ssau-data-engineering-lab2
   ```
2. **Переменные окружения**  
   Скопировать `.env.example` → `.env` и заполнить:
   - `N8N_DOMAIN`, `LETSENCRYPT_EMAIL`, `TZ`.
   - `N8N_ENCRYPTION_KEY`, `N8N_BASIC_AUTH_*`.
   - `POSTGRES_*`.
   - `TELEGRAM_BOT_TOKEN`, `HF_*`/`OPENROUTER` и т.д.
3. **Модель для STT**  
   На сервере скачать и сохранить CTranslate2-веса:
   ```bash
   mkdir -p /opt/models/faster-whisper-small
   python3 - <<'PY'
   from huggingface_hub import snapshot_download
   snapshot_download(
       repo_id="Systran/faster-whisper-small",
       local_dir="/opt/models/faster-whisper-small",
       local_dir_use_symlinks=False,
   )
   PY
   ```
   Каталог подключается в контейнер как `/models/faster-whisper-small`.

4. **SSL / Traefik**  
   Traefik ожидает внешний Docker network `ssau-data-engineering-lab2-dev_web`. нужно создать его один раз:
   ```bash
   docker network create ssau-data-engineering-lab2-dev_web
   ```

## Запуск
```bash
docker compose pull       
docker compose build 
docker compose up -d 
```

## Результат работы

![](image.png)
