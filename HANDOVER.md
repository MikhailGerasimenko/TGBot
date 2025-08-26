# Руководство по передаче проекта (Handover)

Этот документ описывает назначение проекта, архитектуру, конфигурацию, процессы запуска и обслуживания, а также типичные сценарии эксплуатации и отладки. Цель — чтобы новый инженер мог уверенно разворачивать и сопровождать систему без контекстных потерь.

## 1. Назначение проекта
Корпоративный Telegram‑бот с интеграцией LLM. Отвечает на вопросы сотрудников по документации компании, поддерживает регистрацию/верификацию пользователей, поиск по документам (RAG), аналитику и сбор фидбека. Проект разделён на два сервиса:
- model_service: FastAPI сервис с LLM (llama‑cpp), эмбеддингами и гибридным поиском (FAISS+BM25+Cross‑Encoder)
- bot: aiogram‑бот, который взаимодействует с model_service и с пользователем

## 2. Архитектура
- Bot (`bot.py` + `main.py`):
  - Регистрация сотрудников через 1С/БД/файл
  - Обработка команд: /start, /status, /ask, /help, /train, /analytics, /stats, /compare_search
  - Взаимодействие с model_service: поиск контекста и генерация ответа
  - Логи и аналитика в SQLite (`employees.db` по умолчанию)
- Model Service (`model_service.py`):
  - Эндпоинты: /health, /generate, /embed, /index, /search, /search_v2, /usage
  - LLM: llama‑cpp‑python, контекст и температура конфигурируются из .env
  - Поиск: FAISS (dense) + BM25 + Cross‑Encoder (Sentence‑Transformers)
  - Персистентность индекса на диск (`models/search_index.pkl`)

Связь:
- Бот обращается к сервису модели по `MODEL_SERVICE_URL` (например, `http://model_service:8000` в Docker Compose, либо `http://localhost:8000` локально).

## 3. Репозиторий и структура
- `main.py`: точка входа бота
- `bot.py`: хендлеры, бизнес‑логика, интеграция с моделью и документами
- `model_service.py`: сервер модели и поиска
- `database.py`: SQLite/MySQL/MSSQL функции, аналитика
- `oneс_sync.py`: импорт сотрудников из файлов экспорта 1С (csv/json/txt)
- `llm_client.py`: HTTP‑клиент к model_service
- `progress_bars.py`: прогресс‑индикаторы в UI Telegram
- `config.py`: загрузка переменных окружения и создание каталогов
- `docs/`: документы (.docx), которые бот будет индексировать/использовать
- `models/`: GGUF‑модели и файлы индекса (том в Docker)
- `logs/`: логи бота и сервиса модели (том/папка)
- `requirements-bot.txt`, `requirements-service.txt`: разделённые зависимости
- `Dockerfile.bot`, `Dockerfile.model`, `docker-compose.yml`: контейнеризация
- `telegram-bot.service`, `model-service.service`: unit‑файлы systemd (пример)
- `dev.sh`: локальный запуск бота из venv

## 4. Переменные окружения (.env)
Обязательные:
- `API_TOKEN` — токен Telegram бота (из BotFather)
- `ADMIN_CHAT_ID` — Telegram ID администратора
Рекомендуемые:
- `MODEL_SERVICE_URL` — URL сервиса модели (локально `http://localhost:8000`, в Docker — `http://model_service:8000`)
- `GGUF_MODEL_PATH` — путь к GGUF‑модели для сервиса (`/app/models/model-q2_k.gguf` в контейнере)
- `CONFIDENCE_THRESHOLD` — порог уверенности ответов (например, `0.12`)
- `DATABASE_PATH` — путь к SQLite файлу (по умолчанию `employees.db`)
- `USE_SEARCH_V2`, `SEARCH_V2_PERCENTAGE` — A/B конфигурация поиска
Пример см. в `env.example` и README.

## 5. Установка и запуск (без Docker)
1) Python 3.10+ и venv
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements-service.txt   # если нужен локальный model_service
pip install -r requirements-bot.txt
cp env.example .env && nano .env          # заполните токен/конфиг
```
2) Model Service (локально):
```bash
python model_service.py &
# проверьте: curl http://localhost:8000/health
```
3) Бот:
```bash
./dev.sh
# или
python main.py
```

## 6. Установка и запуск (Docker Compose)
1) Подготовьте `.env` и положите модель `.gguf` в каталог `./models`.
2) Соберите и запустите:
```bash
docker compose build
docker compose up -d
```
3) Проверка:
```bash
curl http://localhost:8000/health
docker logs -f telegram_bot
```
Остановка:
```bash
docker compose down
```

## 7. Запуск через systemd (Production)
- Бот: `telegram-bot.service` (использует venv и `main.py`). Обновите `User`, `WorkingDirectory`, путь к `venv/python`.
- Сервис модели: `model-service.service` — при необходимости скорректируйте пути и окружение.
```bash
sudo cp telegram-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable telegram-bot
sudo systemctl start telegram-bot
sudo journalctl -u telegram-bot -f
```

## 8. Индексация документов и поиск
- Добавление документов: админ команда `/train` — загрузить `.docx`, бот разрежет документ на чанки и переиндексирует модель через `/index`.
- Поиск: бот вызывает `/search` или `/search_v2` (по A/B настройке). В ответе показываются топ‑источники и метрика уверенности.

## 9. Регистрация пользователей
- Пользователь отправляет ФИО и табельный номер.
- Проверка: кэш из файла 1С (если указан `ONEC_EXPORT_PATH`) либо БД (`verify_employee` → MSSQL → MySQL → SQLite fallback).
- Анти‑брут: лимит попыток в день, подсказки пользователю, уведомления админу.

## 10. Аналитика и фидбек
- `/analytics` — агрегаты за 7 дней: количество вопросов, среднее время/уверенность, лайки/дизлайки, топ вопросов, неотвеченные.
- `/compare_search` — сравнение v1/v2 по логам и фидбеку.
- Фидбек: кнопки 👍/👎 под ответом, сохраняются в `feedback`.

## 11. Техподдержка и отладка
- Логи:
  - Бот: `logs/bot.log` (и systemd журнал)
  - Модель: `logs/model_service.log` (и stdout контейнера)
- Проверки:
  - `curl http://localhost:8000/health`
  - В БД `qa_sessions` смотреть последние ответы/метрики
- Типичные проблемы:
  - Пустой индекс: загрузить документы или вызвать `/index` через API
  - Медленная генерация на CPU: уменьшить `MAX_NEW_TOKENS`, увеличить `LLAMA_THREADS`, выбрать более компактную модель
  - Ошибки сети к model_service: проверить `MODEL_SERVICE_URL` и статус контейнера

## 12. Обновление и деплой
- Код: стандартный git‑flow, обновления через `git pull` + перезапуск systemd или `docker compose up -d --build`.
- Миграции БД: SQLite схема создаётся автоматически; при переходе на внешние БД подготовьте представления/права чтения.

## 13. Безопасность
- Токены/пароли только в `.env` (никогда в коде)
- Рекомендуется ревокация старых токенов при смене владельца
- Ограничить доступ к БД (read‑only), фильтровать ПДн на уровне документов
- Логи не должны содержать секретов

## 14. Контрольный список перед передачей
- [ ] `.env` заполнен (API_TOKEN, ADMIN_CHAT_ID, MODEL_SERVICE_URL, GGUF_MODEL_PATH)
- [ ] Модель `.gguf` размещена в `models/` (или настроен путь для сервера)
- [ ] Запуск model_service проверен (`/health` ok)
- [ ] Запуск бота проверен (команда `/start` работает)
- [ ] Документы загружены, поиск возвращает результаты
- [ ] systemd/Compose конфиги соответствуют боевому окружению

## 15. Контакты и эскалация
- Вопросы по инфраструктуре: DevOps/Сисадмин
- Вопросы по данным/документам: владельцы контента
- Вопросы по развитию бота/модели: команда разработки 