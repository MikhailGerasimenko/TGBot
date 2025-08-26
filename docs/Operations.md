# Эксплуатация (Operations)

## Аналитика через бота
- `/analytics` — агрегаты за 7 дней: вопросы, среднее время, уверенность, лайки/дизлайки, топы, неотвеченные.
- `/compare_search` — сравнение результатов v1/v2 по логам и фидбеку.

## Логи
- Бот: `logs/bot.log` (или `journalctl -u telegram-bot -f` при systemd).
- Модель: `logs/model_service.log` (или `docker logs -f model_service`).

## Индексация
- Через бота: `/train` — загрузка .docx, «умное» разбиение, вызов `/index`.
- Через API: POST `/index` с массивом текстов.

## Обновления
- Docker: `docker compose pull && docker compose up -d --build`.
- systemd: `git pull && sudo systemctl restart telegram-bot`.

## Бэкапы
- `models/` (индексы, модели), `docs/` (источники), SQLite БД (`employees.db`).

## Типичные проблемы
- Пустой поиск: нет индекса или пустые документы → выполните `/train`/`/index`.
- Низкая уверенность: уточните запрос (дата/подразделение/документ), проверьте `CONFIDENCE_THRESHOLD`.
- Долгая генерация: уменьшите `MAX_NEW_TOKENS`, настройте `LLAMA_THREADS`, используйте более компактную GGUF.
- Ошибка сети: проверьте `MODEL_SERVICE_URL`, `docker ps`, `/health`. 