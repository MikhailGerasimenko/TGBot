#!/bin/bash

echo "=== Установка бота ==="

# Проверка Python
if ! command -v python3 &> /dev/null; then
    echo "Python3 не найден. Установите Python 3.8 или выше"
    exit 1
fi

# Создание виртуального окружения
echo "Создание виртуального окружения..."
python3 -m venv venv
source venv/bin/activate

# Установка зависимостей
echo "Установка зависимостей..."
pip install --upgrade pip
pip install -r requirements.txt

# Проверка системных требований
echo "Проверка системных требований..."
python check_server.py

# Создание директорий
echo "Создание необходимых директорий..."
mkdir -p docs
mkdir -p logs
mkdir -p models

# Подсказка по модели
echo "Если вы используете GGUF, поместите файл модели в models/ и укажите GGUF_MODEL_PATH в .env"

echo "=== Установка завершена ==="
echo "Для запуска бота используйте: python main.py" 