#!/bin/bash

# Скрипт деплоя корпоративного бота в Docker
# Использование: ./deploy.sh [gpu|cpu] [dev|prod]

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функции для вывода
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Проверка аргументов
DEPLOY_TYPE=${1:-cpu}
ENVIRONMENT=${2:-dev}

if [[ "$DEPLOY_TYPE" != "gpu" && "$DEPLOY_TYPE" != "cpu" ]]; then
    log_error "Неверный тип деплоя. Используйте 'gpu' или 'cpu'"
    exit 1
fi

if [[ "$ENVIRONMENT" != "dev" && "$ENVIRONMENT" != "prod" ]]; then
    log_error "Неверное окружение. Используйте 'dev' или 'prod'"
    exit 1
fi

log_info "🚀 Начинаем деплой корпоративного бота"
log_info "Тип: $DEPLOY_TYPE"
log_info "Окружение: $ENVIRONMENT"

# Проверка Docker
if ! command -v docker &> /dev/null; then
    log_error "Docker не установлен"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    log_error "Docker Compose не установлен"
    exit 1
fi

# Проверка .env файла
if [[ ! -f "../.env" ]]; then
    log_error "Файл .env не найден в корневой директории"
    log_info "Скопируйте env.example в .env и настройте параметры"
    exit 1
fi

# Проверка модели для GPU
if [[ "$DEPLOY_TYPE" == "gpu" ]]; then
    if [[ ! -f "../models/model-gigachat_20b_bf16.gguf" ]]; then
        log_warning "BF16 модель не найдена. Скачиваем..."
        cd ..
        ./download_model.sh gigachat_20b_bf16
        cd docker/scripts
    fi
else
    if [[ ! -f "../models/model-gigachat_20b_q8_0.gguf" ]]; then
        log_warning "Q8_0 модель не найдена. Скачиваем..."
        cd ..
        ./download_model.sh gigachat_20b_q8_0
        cd docker/scripts
    fi
fi

# Остановка существующих контейнеров
log_info "🛑 Останавливаем существующие контейнеры..."
cd ..
if [[ "$DEPLOY_TYPE" == "gpu" ]]; then
    docker-compose -f docker/docker-compose.gpu.yml down
else
    docker-compose -f docker/docker-compose.yml down
fi

# Очистка образов (опционально)
if [[ "$ENVIRONMENT" == "prod" ]]; then
    log_info "🧹 Очищаем старые образы..."
    docker system prune -f
fi

# Сборка образов
log_info "🔨 Собираем Docker образы..."
if [[ "$DEPLOY_TYPE" == "gpu" ]]; then
    docker-compose -f docker/docker-compose.gpu.yml build --no-cache
else
    docker-compose -f docker/docker-compose.yml build --no-cache
fi

# Запуск контейнеров
log_info "🚀 Запускаем контейнеры..."
if [[ "$DEPLOY_TYPE" == "gpu" ]]; then
    docker-compose -f docker/docker-compose.gpu.yml up -d
else
    docker-compose -f docker/docker-compose.yml up -d
fi

# Ожидание запуска сервисов
log_info "⏳ Ожидаем запуска сервисов..."
sleep 30

# Проверка статуса
log_info "🔍 Проверяем статус сервисов..."
if [[ "$DEPLOY_TYPE" == "gpu" ]]; then
    docker-compose -f docker/docker-compose.gpu.yml ps
else
    docker-compose -f docker/docker-compose.yml ps
fi

# Проверка health check
log_info "🏥 Проверяем health check..."
sleep 10

# Проверка model service
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    log_success "✅ Model Service работает"
else
    log_error "❌ Model Service не отвечает"
    log_info "Проверьте логи: docker-compose logs model-service"
fi

# Проверка nginx
if curl -f http://localhost:80 > /dev/null 2>&1; then
    log_success "✅ Nginx работает"
else
    log_error "❌ Nginx не отвечает"
fi

# Вывод информации
log_success "🎉 Деплой завершен!"
echo ""
log_info "📊 Статус сервисов:"
if [[ "$DEPLOY_TYPE" == "gpu" ]]; then
    docker-compose -f docker/docker-compose.gpu.yml ps
else
    docker-compose -f docker/docker-compose.yml ps
fi

echo ""
log_info "🔗 Доступные URL:"
echo "  - API: http://localhost:8000"
echo "  - Nginx: http://localhost:80"
echo "  - Health Check: http://localhost:8000/health"

if [[ "$DEPLOY_TYPE" == "gpu" ]]; then
    echo "  - Grafana: http://localhost:3000 (admin/admin)"
fi

echo ""
log_info "📝 Полезные команды:"
echo "  - Логи: docker-compose -f docker/docker-compose.yml logs -f"
echo "  - Остановка: docker-compose -f docker/docker-compose.yml down"
echo "  - Перезапуск: docker-compose -f docker/docker-compose.yml restart"

if [[ "$DEPLOY_TYPE" == "gpu" ]]; then
    echo "  - GPU мониторинг: nvidia-smi"
fi

echo ""
log_success "🤖 Корпоративный бот готов к работе!" 