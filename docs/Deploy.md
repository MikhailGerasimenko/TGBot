# Деплой (Docker Compose и systemd)

## Docker Compose (рекомендовано)
1. Подготовьте `.env` и положите модель `.gguf` в `./models/`.
2. Соберите и поднимите:
```bash
docker compose build
docker compose up -d
```
3. Проверка:
```bash
curl http://localhost:8000/health
docker logs -f telegram_bot
```
4. Остановка:
```bash
docker compose down
```

### Настройки
- Переменные берутся из `.env` и секций `environment` в `docker-compose.yml`.
- Том `./models` хранит индекс и модели (персистентность).

## systemd (альтернатива)
- Бот: `telegram-bot.service` — обновите `User`, `WorkingDirectory`, путь к `venv/python`.
- Модель: `model-service.service` — скорректируйте пути под сервер.
```bash
sudo cp telegram-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable telegram-bot
sudo systemctl start telegram-bot
sudo journalctl -u telegram-bot -f
```

## Рекомендации продакшн
- Non‑root образы/пользователи в контейнерах.
- Мониторинг (метрики/логи) и алёрты.
- Бэкапы: `models/`, `docs/`, SQLite‑файл БД. 