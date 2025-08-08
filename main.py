import asyncio
import logging
from aiogram import Bot, Dispatcher
from bot import bot, periodic_sync, setup_handlers
from database import init_db, populate_test_data

# Настройка логирования (подробная настройка в bot.py)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)

logger = logging.getLogger(__name__)

async def main():
    try:
        # Инициализация базы данных
        logger.info("Инициализация базы данных...")
        await init_db()
        await populate_test_data()
        
        # Создаем диспетчер
        dp = Dispatcher()
        
        # Регистрируем все хендлеры
        setup_handlers(dp)
        
        # Запуск периодической синхронизации
        asyncio.create_task(periodic_sync())
        
        # Запуск бота
        logger.info("Запуск бота...")
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
    finally:
        await bot.session.close()

if __name__ == '__main__':
    asyncio.run(main())
