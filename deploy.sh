#!/bin/bash

# Проверяем наличие аргумента с сообщением коммита
if [ "$#" -ne 1 ]; then
    echo "Использование: ./deploy.sh 'сообщение коммита'"
    exit 1
fi

echo "=== Деплой изменений на сервер ==="

# Проверка синтаксиса перед коммитом
echo "Проверка синтаксиса..."
python -m py_compile main.py bot.py database.py
if [ $? -ne 0 ]; then
    echo "❌ Ошибка в синтаксисе Python! Отмена деплоя..."
    exit 1
fi

# Добавление и коммит изменений
echo "Коммит изменений..."
git add .
git commit -m "$1"

# Отправка изменений на сервер
echo "Отправка изменений..."
git push

# Подключение к серверу и обновление
echo "Обновление на сервере..."
ssh bot@your-server.com "cd telegram-bot && ./update.sh"

echo "✅ Деплой завершен!" 