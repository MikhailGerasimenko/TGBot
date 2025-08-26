# Корпоративный Telegram Бот с LLM

> Полное руководство: HANDOVER.md. Подробная документация: docs/Architecture.md, docs/Setup.md, docs/Deploy.md, docs/API.md, docs/Operations.md, docs/Security.md, docs/Quality.md

Telegram‑бот для корпоративной поддержки с использованием LLM и RAG (Retrieval Augmented Generation): отвечает на вопросы по регламентам/SOP/FAQ, показывает источники, учитывает уверенность и собирает фидбек.

## Особенности

- Регистрация с верификацией (MSSQL/MySQL/SQLite или файл выгрузки 1С), анти‑брутфорс
- Интеграция с LLM (llama‑cpp), гибридный поиск (FAISS + BM25), Cross‑Encoder реранкинг
- Query Expansion, порог уверенности и логирование «неотвеченных»
- Загрузка .docx с «умным» разбиением и индексацией через API сервиса
- Аналитика и A/B‑тест (/analytics, /compare_search, фидбек 👍/👎)
- Персистентность индекса, healthcheck, Docker/Compose и systemd

## Архитектура

- Model Service (`model_service.py`, FastAPI): `/health`, `/generate`, `/embed`, `/index`, `/search`, `/search_v2`, `/usage`
- Telegram Bot (`bot.py` + `main.py`, aiogram v3): команды, UX, интеграции, аналитика
- БД/данные: SQLite (по умолч.), MySQL/MSSQL (через aio*), выгрузки 1С (CSV/JSON/TXT)

## Требования

- Python 3.10+ (локальный запуск) или Docker (рекомендуется)
- Для Model Service: зависимости из `requirements-service.txt`
- Для Bot: зависимости из `requirements-bot.txt`

## Установка

1) Клонировать репозиторий
```bash
git clone https://github.com/MikhailGerasimenko/TGBot.git
cd TGBot
```

2) Виртуальное окружение
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate    # Windows
```

3) Зависимости
```bash
# Бот
pip install -r requirements-bot.txt
# Сервис модели (если запускаете локально)
pip install -r requirements-service.txt
```

4) Конфигурация `.env`
```bash
cp env.example .env
# Заполните хотя бы API_TOKEN, ADMIN_CHAT_ID, MODEL_SERVICE_URL, GGUF_MODEL_PATH
```

## Запуск

### Вариант A — локально (CPU)
1) Сервис модели:
```bash
python model_service.py
# проверка
curl http://localhost:8000/health
```
2) Бот:
```bash
./dev.sh   # или python main.py
```

Пример путей для `.env` (локально):
```env
MODEL_SERVICE_URL=http://localhost:8000
GGUF_MODEL_PATH=models/model-q2_k.gguf
```

### Вариант B — Docker Compose
```bash
docker compose build
docker compose up -d
# healthcheck
curl http://localhost:8000/health
```
В Compose сервис бота видит модель по `MODEL_SERVICE_URL=http://model_service:8000`. Путь к модели внутри контейнера: `/app/models/model-q2_k.gguf`.

### Вариант C — systemd (бот)
```bash
sudo cp telegram-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable telegram-bot
sudo systemctl start telegram-bot
sudo journalctl -u telegram-bot -f
```

## Команды бота

- Пользователь: `/start`, `'повтор'`, `/cancel`, `/status`, `/ask`, `/help`
- Админ: `/train`, `/analytics`, `/stats`, `/compare_search`

## Основные переменные `.env`

```env
# Telegram
API_TOKEN=your_bot_token
ADMIN_CHAT_ID=your_admin_id

# Model Service
# Локально:
MODEL_SERVICE_URL=http://localhost:8000
GGUF_MODEL_PATH=models/model-q2_k.gguf
# В Docker:
# MODEL_SERVICE_URL=http://model_service:8000
# GGUF_MODEL_PATH=/app/models/model-q2_k.gguf
LLAMA_CTX=2048
LLAMA_THREADS=4
LLAMA_BATCH=256
LLAMA_GPU_LAYERS=0
MAX_NEW_TOKENS=512
MONTHLY_TOKEN_LIMIT=10000000
TOKEN_ALERT_THRESHOLD=0.8

# RAG
EMBEDDING_MODEL_NAME=paraphrase-multilingual-MiniLM-L12-v2
CROSS_ENCODER_MODEL=cross-encoder/ms-marco-MiniLM-L-12-v2
USE_SEARCH_V2=false
SEARCH_V2_PERCENTAGE=30
CONFIDENCE_THRESHOLD=0.12

# Database
DATABASE_PATH=employees.db
# MySQL (опционально)
MYSQL_HOST=
MYSQL_PORT=3306
MYSQL_DB=
MYSQL_USER=
MYSQL_PASSWORD=
# MS SQL Server (опционально)
MSSQL_DSN=
MSSQL_HOST=
MSSQL_PORT=1433
MSSQL_DB=
MSSQL_USER=
MSSQL_PASSWORD=

# Redis (если используется)
REDIS_URL=redis://localhost:6379/0

# 1C выгрузка (файл)
ONEC_EXPORT_PATH=

# Логи
LOG_LEVEL=INFO
```

## Dev‑скрипт

`dev.sh` запускает бота из venv:
```bash
#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"
source venv/bin/activate
python main.py
```

## Безопасность

- Секреты только в `.env`, без хардкодов
- Минимальные права к БД (read‑only), защита ПДн, скрытие секретов в логах
- Таймауты HTTP, healthcheck, перезапуски (Compose/systemd)

## Производительность

- CPU: уменьшайте `MAX_NEW_TOKENS`, подбирайте `LLAMA_THREADS`
- GPU (опционально): увеличивайте `LLAMA_GPU_LAYERS`
- Персистентный индекс в `models/`, быстрые рестарты

---
Подробности: HANDOVER.md и `docs/` (архитектура, деплой, API, эксплуатация, безопасность, качество).

