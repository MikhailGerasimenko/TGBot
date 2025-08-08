#!/bin/bash

echo "=== Запуск бота в режиме разработки ==="

# Активация виртуального окружения
if [ ! -d "venv" ]; then
    echo "Создание виртуального окружения..."
    python3 -m venv venv
fi

source venv/bin/activate

# Установка зависимостей
echo "Проверка зависимостей..."
pip install -r requirements.txt

# Проверка синтаксиса
echo "Проверка синтаксиса..."
python -m py_compile main.py bot.py database.py
if [ $? -ne 0 ]; then
    echo "❌ Ошибка в синтаксисе Python!"
    exit 1
fi

# Запуск бота
echo "Запуск бота..."
python main.py 