# Установка и локальный запуск

## Требования
- Python 3.10+ (рекомендуется 3.11)
- Git, Bash, Linux/macOS (Windows WSL2)

## Клонирование и окружение
```bash
git clone <repo>
cd <repo>
./setup.sh
# создает venv, ставит зависимости, подготавливает .env
```

## Конфигурация `.env`
Критично заполнить:
- `API_TOKEN` (BotFather)
- `ADMIN_CHAT_ID` (ваш Telegram ID)
- `MODEL_SERVICE_URL` (локально: `http://localhost:8000`)
- `GGUF_MODEL_PATH` (путь к модели для сервиса)

## Локальный Model Service
```bash
source venv/bin/activate
python model_service.py
# проверка
curl http://localhost:8000/health
```

## Запуск бота
```bash
source venv/bin/activate
./dev.sh
# или
python main.py
```

## Загрузка документов
- Админ отправляет боту .docx командой `/train` — документы попадают в `docs/`, сервис переиндексируется.

## Проверка поиска/генерации
- В боте: `/ask` → вопрос.
- При низкой уверенности ответ не выдается, вопрос логируется как «неотвеченный» для последующей обработки. 