# Корпоративный Telegram Бот с LLM

> Полное руководство: HANDOVER.md. Подробная документация: docs/Architecture.md, docs/Setup.md, docs/Deploy.md, docs/API.md, docs/Operations.md, docs/Security.md, docs/Quality.md

Telegram бот для корпоративной поддержки с использованием Language Model (LLM) для ответов на вопросы и обработки документации. Реализует современные методы RAG (Retrieval Augmented Generation)

## Особенности

- 🤖 Регистрация пользователей с верификацией (MySQL/MSSQL/SQLite или файл выгрузки)
- 🧠 Интеграция с LLM (Saiga-2, llama-cpp) для ответов на вопросы
- 📚 **Продвинутый RAG (Retrieval Augmented Generation)**:
  - **Cross-Encoder переранжирование** для повышения точности поиска
  - **Query Expansion** - автоматическое расширение запросов через LLM
  - **Гибридный поиск**: FAISS (dense) + BM25 + Cross-Encoder реранкинг
  - **Умное разбиение документов** с метаданными (тип, отдел, даты)
  - **Персистентность индекса** - сохранение на диск для быстрого запуска
  - **A/B тестирование** версий поиска с автоматическим распределением
  - Отображение «Источников» в ответе и порог уверенности
- 📊 **Расширенная аналитика и мониторинг**:
  - Метрики времени ответа, уверенности, популярных вопросов
  - Система фидбека с кнопками 👍👎 для оценки ответов
  - Сбор неотвеченных вопросов для улучшения базы знаний
  - Сравнение эффективности разных версий поиска
- 🔄 Асинхронная обработка запросов, периодическая синхронизация сотрудников
- 🧭 Улучшенный UX: /status, /cancel, «повтор» после неуспешной регистрации
- 🎯 **Админ-панель**: загрузка документов, аналитика, A/B тестирование

## Архитектура

Проект разделен на два основных компонента:

### 1. **Model Service** (model_service.py):
   - FastAPI сервер для LLM (llama-cpp)
   - **Многоязычная модель эмбеддингов** Sentence-Transformers
   - **Cross-Encoder** для точного переранжирования результатов
   - **Гибридный поиск**: FAISS + BM25 + Cross-Encoder
   - **Персистентность индекса** с проверкой актуальности
   - Эндпоинты:
     - GET `/health` - статус сервиса и метрики
     - POST `/generate` - генерация ответов
     - POST `/embed` - создание эмбеддингов
     - POST `/index` - индексация массива текстов
     - POST `/search` - классический гибридный поиск
     - POST `/search_v2` - улучшенный поиск с Cross-Encoder
     - POST `/usage` - статистика использования токенов

### 2. **Telegram Bot** (bot.py + main.py):
   - Регистрация и верификация пользователей
   - **Query Expansion** для улучшения поиска
   - **A/B тестирование** версий поиска
   - Интеграция с Model Service (v1/v2 поиск + генерация)
   - **Умное разбиение документов** при загрузке
   - **Система фидбека** с кнопками оценки
   - **Расширенная аналитика** использования

## Требования

### Для Model Service:
- Python 3.8+
- NVIDIA GPU (опционально) — для ускорения указать `LLAMA_GPU_LAYERS`
- 8–24GB RAM (в зависимости от модели)
- Устанавливать зависимости из `requirements-service.txt`

### Для Telegram Bot:
- Python 3.8+
- 4GB RAM
- Устанавливать зависимости из `requirements-bot.txt`

## Установка

1. Клонируйте репозиторий:
```bash
git clone https://github.com/your-username/your-repo.git
cd your-repo
```

2. Создайте виртуальное окружение:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows
```

3. Установите зависимости:
```bash
# для бота
a pip install -r requirements-bot.txt
# для сервиса модели
a pip install -r requirements-service.txt
```

4. Создайте файл .env:
```bash
cp env.example .env
# Отредактируйте .env, добавив свои значения
```

## Запуск

### Model Service (на сервере):

1. Укажите путь к GGUF в `.env`:
```env
GGUF_MODEL_PATH=/home/bot/models/saiga2_7b_q4_k_m.gguf
LLAMA_CTX=2048
LLAMA_THREADS=4
LLAMA_BATCH=256
LLAMA_GPU_LAYERS=32

# RAG Configuration
EMBEDDING_MODEL_NAME=paraphrase-multilingual-MiniLM-L12-v2
CROSS_ENCODER_MODEL=cross-encoder/ms-marco-MiniLM-L-12-v2
USE_SEARCH_V2=false
SEARCH_V2_PERCENTAGE=30
CONFIDENCE_THRESHOLD=0.12
```

2. Запуск:
```bash
python model_service.py
# или через systemd (рекомендуется)
sudo cp model-service.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable model-service
sudo systemctl start model-service
```

3. Индексация для гибридного поиска (опционально через API):
```bash
curl -X POST http://localhost:8000/index \
  -H 'Content-Type: application/json' \
  -d '{"documents":["текст_документа_1","текст_документа_2"]}'
```

4. Поиск (проверка):
```bash
# Классический поиск
curl -X POST http://localhost:8000/search \
  -H 'Content-Type: application/json' \
  -d '{"query":"ваш вопрос","top_k":3}'

# Улучшенный поиск с Cross-Encoder
curl -X POST http://localhost:8000/search_v2 \
  -H 'Content-Type: application/json' \
  -d '{"query":"ваш вопрос","top_k":3}'
```

### Telegram Bot:

1. Для разработки:
```bash
./dev.sh
```

2. Для production:
```bash
sudo cp telegram-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable telegram-bot
sudo systemctl start telegram-bot
```

## Команды бота

### Пользовательские команды:
- `/start` — регистрация (ФИО + табельный)
- `'повтор'` — повторить попытку регистрации (кнопка появляется при ошибке)
- `/cancel` — отменить текущую операцию
- `/status` — профиль пользователя (после регистрации)
- `/ask` — задать вопрос ассистенту (после регистрации)
- `/help` — помощь (после регистрации)

### Админ-команды:
- `/train` — загрузить .docx документ; бот индексирует с умным разбиением
- `/analytics` — подробная статистика использования за 7 дней
- `/stats` — краткая статистика (алиас для analytics)
- `/compare_search` — сравнение эффективности v1 и v2 поиска (A/B тест)

## Конфигурация

Основные настройки в файле `.env`:

```env
# Telegram
API_TOKEN=your_bot_token
ADMIN_CHAT_ID=your_admin_id

# Model Service
MODEL_SERVICE_URL=http://your-server:8000
GGUF_MODEL_PATH=/path/to/model.gguf
LLAMA_CTX=2048
LLAMA_THREADS=4
LLAMA_BATCH=256
LLAMA_GPU_LAYERS=32
MAX_NEW_TOKENS=512
MONTHLY_TOKEN_LIMIT=10000000
TOKEN_ALERT_THRESHOLD=0.8

# RAG Configuration
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

# Redis
REDIS_URL=redis://localhost:6379/0

# 1C Integration
ONEC_EXPORT_PATH=

# Logging
LOG_LEVEL=INFO
```

## Dev скрипт

Файл `dev.sh` запускает бота в активированном venv:
```bash
#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"
source venv/bin/activate
python main.py
```
Сделайте исполняемым: `chmod +x dev.sh`.

## Безопасность

- Храните секреты только в `.env`
- Для БД используйте read‑only пользователя и ограничивайте права
- Фильтруйте ПДн в ответах; применяйте ACL к документам
- Мониторьте использование токенов через `/usage`

## Производительность

- GPU ускорение: `LLAMA_GPU_LAYERS`
- Кеширование состояний: Redis
- Мониторинг: аналитика в боте + логи сервиса модели
- Масштабирование: несколько экземпляров `model_service` за балансировщиком

