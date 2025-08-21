#!/bin/bash

# Скрипт управления корпоративным ботом в Docker
# Использование: ./manage.sh [start|stop|restart|logs|status|update]

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

# Определение типа деплоя
get_deploy_type() {
    if docker ps | grep -q "corporate-bot-model-gpu"; then
        echo "gpu"
    elif docker ps | grep -q "corporate-bot-model"; then
        echo "cpu"
    else
        echo "unknown"
    fi
}

# Получение compose файла
get_compose_file() {
    local deploy_type=$1
    if [[ "$deploy_type" == "gpu" ]]; then
        echo "docker/docker-compose.gpu.yml"
    else
        echo "docker/docker-compose.yml"
    fi
}

# Проверка аргументов
if [[ $# -eq 0 ]]; then
    echo "Использование: $0 [start|stop|restart|logs|status|update|backup|restore]"
    echo ""
    echo "Команды:"
    echo "  start   - Запуск всех сервисов"
    echo "  stop    - Остановка всех сервисов"
    echo "  restart - Перезапуск всех сервисов"
    echo "  logs    - Просмотр логов"
    echo "  status  - Статус сервисов"
    echo "  update  - Обновление кода и перезапуск"
    echo "  backup  - Резервное копирование данных"
    echo "  restore - Восстановление из резервной копии"
    exit 1
fi

COMMAND=$1
SERVICE=${2:-""}

# Переход в корневую директорию
cd "$(dirname "$0")/../.."

# Проверка Docker
if ! command -v docker &> /dev/null; then
    log_error "Docker не установлен"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    log_error "Docker Compose не установлен"
    exit 1
fi

# Определение типа деплоя
DEPLOY_TYPE=$(get_deploy_type)
COMPOSE_FILE=$(get_compose_file $DEPLOY_TYPE)

if [[ "$DEPLOY_TYPE" == "unknown" ]]; then
    log_warning "Не удалось определить тип деплоя. Используем CPU по умолчанию."
    DEPLOY_TYPE="cpu"
    COMPOSE_FILE="docker/docker-compose.yml"
fi

log_info "Тип деплоя: $DEPLOY_TYPE"
log_info "Compose файл: $COMPOSE_FILE"

case $COMMAND in
    start)
        log_info "🚀 Запуск сервисов..."
        docker-compose -f $COMPOSE_FILE up -d
        log_success "Сервисы запущены"
        ;;
        
    stop)
        log_info "🛑 Остановка сервисов..."
        docker-compose -f $COMPOSE_FILE down
        log_success "Сервисы остановлены"
        ;;
        
    restart)
        log_info "🔄 Перезапуск сервисов..."
        docker-compose -f $COMPOSE_FILE restart
        log_success "Сервисы перезапущены"
        ;;
        
    logs)
        if [[ -n "$SERVICE" ]]; then
            log_info "📋 Логи сервиса $SERVICE:"
            docker-compose -f $COMPOSE_FILE logs -f $SERVICE
        else
            log_info "📋 Логи всех сервисов:"
            docker-compose -f $COMPOSE_FILE logs -f
        fi
        ;;
        
    status)
        log_info "📊 Статус сервисов:"
        docker-compose -f $COMPOSE_FILE ps
        
        echo ""
        log_info "🔍 Проверка health check:"
        
        # Проверка model service
        if curl -f http://localhost:8000/health > /dev/null 2>&1; then
            log_success "✅ Model Service работает"
        else
            log_error "❌ Model Service не отвечает"
        fi
        
        # Проверка nginx
        if curl -f http://localhost:80 > /dev/null 2>&1; then
            log_success "✅ Nginx работает"
        else
            log_error "❌ Nginx не отвечает"
        fi
        
        # Проверка Redis
        if docker exec corporate-bot-redis redis-cli ping > /dev/null 2>&1; then
            log_success "✅ Redis работает"
        else
            log_error "❌ Redis не отвечает"
        fi
        
        if [[ "$DEPLOY_TYPE" == "gpu" ]]; then
            echo ""
            log_info "🖥️ GPU статус:"
            nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu --format=csv
        fi
        ;;
        
    update)
        log_info "🔄 Обновление системы..."
        
        # Остановка сервисов
        docker-compose -f $COMPOSE_FILE down
        
        # Обновление кода (если используется git)
        if [[ -d ".git" ]]; then
            log_info "📥 Обновление кода из git..."
            git pull origin main
        fi
        
        # Пересборка образов
        log_info "🔨 Пересборка образов..."
        docker-compose -f $COMPOSE_FILE build --no-cache
        
        # Запуск сервисов
        log_info "🚀 Запуск обновленных сервисов..."
        docker-compose -f $COMPOSE_FILE up -d
        
        log_success "Система обновлена"
        ;;
        
    backup)
        log_info "💾 Создание резервной копии..."
        
        BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
        mkdir -p $BACKUP_DIR
        
        # Резервное копирование БД
        if [[ -f "data/employees.db" ]]; then
            cp data/employees.db $BACKUP_DIR/
            log_success "База данных скопирована"
        fi
        
        # Резервное копирование документов
        if [[ -d "documents" ]]; then
            cp -r documents $BACKUP_DIR/
            log_success "Документы скопированы"
        fi
        
        # Резервное копирование конфигурации
        if [[ -f ".env" ]]; then
            cp .env $BACKUP_DIR/
            log_success "Конфигурация скопирована"
        fi
        
        # Создание архива
        tar -czf "${BACKUP_DIR}.tar.gz" -C backups $(basename $BACKUP_DIR)
        rm -rf $BACKUP_DIR
        
        log_success "Резервная копия создана: ${BACKUP_DIR}.tar.gz"
        ;;
        
    restore)
        if [[ -z "$SERVICE" ]]; then
            log_error "Укажите путь к резервной копии"
            echo "Использование: $0 restore <backup_file.tar.gz>"
            exit 1
        fi
        
        log_info "📥 Восстановление из резервной копии..."
        
        if [[ ! -f "$SERVICE" ]]; then
            log_error "Файл резервной копии не найден: $SERVICE"
            exit 1
        fi
        
        # Остановка сервисов
        docker-compose -f $COMPOSE_FILE down
        
        # Извлечение архива
        RESTORE_DIR="backups/restore_$(date +%Y%m%d_%H%M%S)"
        mkdir -p $RESTORE_DIR
        tar -xzf "$SERVICE" -C $RESTORE_DIR
        
        # Восстановление файлов
        if [[ -f "$RESTORE_DIR/data/employees.db" ]]; then
            cp "$RESTORE_DIR/data/employees.db" data/
            log_success "База данных восстановлена"
        fi
        
        if [[ -d "$RESTORE_DIR/documents" ]]; then
            cp -r "$RESTORE_DIR/documents" ./
            log_success "Документы восстановлены"
        fi
        
        if [[ -f "$RESTORE_DIR/.env" ]]; then
            cp "$RESTORE_DIR/.env" ./
            log_success "Конфигурация восстановлена"
        fi
        
        # Очистка
        rm -rf $RESTORE_DIR
        
        # Запуск сервисов
        docker-compose -f $COMPOSE_FILE up -d
        
        log_success "Восстановление завершено"
        ;;
        
    *)
        log_error "Неизвестная команда: $COMMAND"
        echo "Используйте: start, stop, restart, logs, status, update, backup, restore"
        exit 1
        ;;
esac 