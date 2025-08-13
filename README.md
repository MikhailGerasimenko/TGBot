# Корпоративный Telegram Бот с LLM

Telegram бот для корпоративной поддержки с использованием Language Model (LLM) для ответов на вопросы и обработки документации.

## Особенности

- 🤖 Регистрация пользователей с верификацией (MySQL/MSSQL/SQLite или файл выгрузки)
- 🧠 Интеграция с LLM (Saiga-2, llama-cpp) для ответов на вопросы
- 📚 RAG (Retrieval Augmented Generation):
  - Локальная индексация .docx (в боте)
  - Гибридный поиск в сервисе модели: FAISS (dense) + BM25 + реранкинг косинусом
  - Отображение «Источников» в ответе и порог уверенности
- 🔄 Асинхронная обработка запросов, периодическая синхронизация сотрудников
- 🧭 Улучшенный UX: /status, /cancel, «повтор» после неуспешной регистрации; команды /ask и /help доступны только после регистрации
- 📊 Мониторинг и логирование

## Архитектура

Проект разделен на два основных компонента:

1. **Model Service** (model_service.py):
   - FastAPI сервер для LLM (llama-cpp)
   - Модель эмбеддингов Sentence-Transformers
   - Гибридный поиск: FAISS (HNSW FlatIP) + BM25, реранкинг косинусом
   - Эндпоинты:
     - GET `/health`
     - POST `/generate`
     - POST `/embed`
     - POST `/index` — индексировать массив текстов
     - POST `/search` — гибридный поиск с выдачей top-k

2. **Telegram Bot** (bot.py):
   - Регистрация и верификация
   - Интеграция с Model Service (/search + /generate)
   - /train — загрузка .docx, локальная индексация и отправка текста в `/index`
   - Ответы с кратким списком источников и проверкой уверенности

## Требования

### Для Model Service:
- Python 3.8+
- NVIDIA GPU (опционально) — для ускорения указать `LLAMA_GPU_LAYERS`
- 8–24GB RAM (в зависимости от модели)

### Для Telegram Bot:
- Python 3.8+
- 4GB RAM

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
pip install -r requirements.txt
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
curl -X POST http://localhost:8000/search \
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
sudo systemctl enable telegram-bot
sudo systemctl start telegram-bot
```

## Команды бота

- `/start` — регистрация (ФИО + табельный)
- `'повтор'` — повторить попытку регистрации (кнопка появляется при ошибке)
- `/cancel` — отменить текущую операцию
- `/status` — профиль пользователя (после регистрации)
- `/ask` — задать вопрос ассистенту (после регистрации)
- `/help` — помощь (после регистрации)
- `/train` — админ: загрузить .docx; бот индексирует локально и отправляет текст в `/index`

Поведение при вопросах:
- Бот делает гибридный поиск (FAISS+BM25) через `/search` и реранкит кандидаты
- Если уверенность низкая — просит уточнить запрос
- В ответ добавляется блок «Источники» (score)

## Разработка

1. Настройка окружения:
```bash
pip install -r requirements.txt
```

2. Запуск тестов (при наличии):
```bash
python -m pytest tests/
```

3. Проверка кода:
```bash
python -m py_compile main.py bot.py database.py
flake8 .
```

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

# Logging
LOG_LEVEL=INFO

# 1C export (Variant A — опционально)
ONEC_EXPORT_PATH=/absolute/path/to/employees.csv
```

## Мониторинг

1. Логи бота:
```bash
tail -f logs/bot.log
```

2. Логи модели:
```bash
tail -f logs/model_service.log
```

3. Системные логи:
```bash
sudo journalctl -u telegram-bot -f
sudo journalctl -u model-service -f
```

## Безопасность

- Используйте .env/секрет‑хранилище для токенов и доступов
- Для БД создавайте read‑only пользователя и ограничивайте права до нужных представлений
- Фильтруйте ПДн в ответах и применяйте ACL к документам

## Лицензия

MIT

