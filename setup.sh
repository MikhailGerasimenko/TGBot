#!/usr/bin/env bash
set -euo pipefail

# Создание venv
if [ ! -d "venv" ]; then
  python3 -m venv venv
fi
source venv/bin/activate

# Установка зависимостей
pip install --upgrade pip
if [ -f requirements-service.txt ]; then
  pip install -r requirements-service.txt || true
fi
pip install -r requirements-bot.txt

# Создание .env, если отсутствует
if [ ! -f .env ]; then
  cp env.example .env
  echo "Создан .env (заполните API_TOKEN, ADMIN_CHAT_ID)"
fi

echo "Готово. Запуск бота: ./dev.sh" 