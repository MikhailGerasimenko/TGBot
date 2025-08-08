import sqlite3
import aiofiles
import aiosqlite
from datetime import datetime
import logging
from config import DATABASE_PATH

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_PATH = DATABASE_PATH

# SQL для создания таблиц
INIT_SQL = """
CREATE TABLE IF NOT EXISTS employees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    employee_id TEXT NOT NULL UNIQUE,
    department TEXT,
    position TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS registration_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER NOT NULL,
    full_name TEXT NOT NULL,
    employee_id TEXT NOT NULL,
    success BOOLEAN NOT NULL,
    attempt_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

# Тестовые данные
TEST_DATA = [
    ("Иванов Иван Иванович", "E001", "IT отдел", "Программист"),
    ("Петров Петр Петрович", "E002", "Бухгалтерия", "Главный бухгалтер"),
    ("Сидорова Анна Владимировна", "E003", "HR отдел", "HR менеджер"),
    ("Козлов Дмитрий Сергеевич", "E004", "IT отдел", "Системный администратор"),
    ("Морозова Елена Александровна", "E005", "Отдел продаж", "Менеджер по продажам")
]

async def init_db():
    """Инициализация базы данных"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.executescript(INIT_SQL)
            await db.commit()
            
        logger.info("База данных успешно инициализирована")
        return True
    except Exception as e:
        logger.error(f"Ошибка при инициализации базы данных: {e}")
        return False

async def populate_test_data():
    """Заполнение тестовыми данными"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # Проверяем, есть ли уже данные
            async with db.execute("SELECT COUNT(*) FROM employees") as cursor:
                count = await cursor.fetchone()
                if count[0] > 0:
                    logger.info("Тестовые данные уже существуют")
                    return True
            
            # Добавляем тестовые данные
            await db.executemany(
                "INSERT INTO employees (full_name, employee_id, department, position) VALUES (?, ?, ?, ?)",
                TEST_DATA
            )
            await db.commit()
            
        logger.info("Тестовые данные успешно добавлены")
        return True
    except Exception as e:
        logger.error(f"Ошибка при добавлении тестовых данных: {e}")
        return False

async def verify_employee(full_name: str, employee_id: str) -> dict:
    """Проверка сотрудника в базе данных"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """SELECT * FROM employees 
                WHERE full_name = ? AND employee_id = ?""",
                (full_name, employee_id)
            ) as cursor:
                employee = await cursor.fetchone()
                
                if employee:
                    return {
                        "verified": True,
                        "department": employee["department"],
                        "position": employee["position"],
                        "employee_id": employee["employee_id"]
                    }
                return {"verified": False}
    except Exception as e:
        logger.error(f"Ошибка при проверке сотрудника: {e}")
        return {"verified": False, "error": str(e)}

async def log_registration_attempt(telegram_id: int, full_name: str, employee_id: str, success: bool):
    """Логирование попытки регистрации"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                """INSERT INTO registration_attempts 
                (telegram_id, full_name, employee_id, success) 
                VALUES (?, ?, ?, ?)""",
                (telegram_id, full_name, employee_id, success)
            )
            await db.commit()
        return True
    except Exception as e:
        logger.error(f"Ошибка при логировании попытки регистрации: {e}")
        return False

async def get_registration_attempts(telegram_id: int) -> list:
    """Получение истории попыток регистрации"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """SELECT * FROM registration_attempts 
                WHERE telegram_id = ? 
                ORDER BY attempt_time DESC""",
                (telegram_id,)
            ) as cursor:
                return await cursor.fetchall()
    except Exception as e:
        logger.error(f"Ошибка при получении истории попыток: {e}")
        return []

# Функция для получения всех сотрудников (аналог синхронизации с 1С)
async def get_all_employees() -> list:
    """Получение списка всех сотрудников"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM employees") as cursor:
                employees = await cursor.fetchall()
                return [dict(emp) for emp in employees]
    except Exception as e:
        logger.error(f"Ошибка при получении списка сотрудников: {e}")
        return [] 