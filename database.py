import sqlite3
import aiofiles
import aiosqlite
from datetime import datetime
import logging
from config import DATABASE_PATH, MYSQL_HOST, MYSQL_PORT, MYSQL_DB, MYSQL_USER, MYSQL_PASSWORD, MSSQL_DSN, MSSQL_HOST, MSSQL_PORT, MSSQL_DB, MSSQL_USER, MSSQL_PASSWORD
import os

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

# ===== MSSQL helpers =====

def _mssql_enabled() -> bool:
    return bool(MSSQL_DSN or (MSSQL_HOST and MSSQL_DB and MSSQL_USER))

async def _mssql_get_pool():
    import aioodbc
    if MSSQL_DSN:
        return await aioodbc.create_pool(dsn=MSSQL_DSN, autocommit=True, minsize=1, maxsize=5)
    conn_str = (
        f"DRIVER={{ODBC Driver 18 for SQL Server}};"
        f"SERVER={MSSQL_HOST},{MSSQL_PORT};"
        f"DATABASE={MSSQL_DB};"
        f"UID={MSSQL_USER};PWD={MSSQL_PASSWORD};"
        f"TrustServerCertificate=Yes;"
    )
    return await aioodbc.create_pool(dsn=conn_str, autocommit=True, minsize=1, maxsize=5)

# ===== MySQL helpers =====

def _mysql_enabled() -> bool:
    return all([MYSQL_HOST, MYSQL_DB, MYSQL_USER]) and not _mssql_enabled()

async def _mysql_get_pool():
    import aiomysql
    return await aiomysql.create_pool(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        db=MYSQL_DB,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        autocommit=True,
        minsize=1,
        maxsize=5,
        charset='utf8mb4'
    )

async def verify_employee(full_name: str, employee_id: str) -> dict:
    """Проверка сотрудника: MSSQL -> MySQL -> SQLite."""
    # MSSQL
    if _mssql_enabled():
        try:
            pool = await _mssql_get_pool()
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        """
                        SELECT department, position FROM employees
                        WHERE full_name = ? AND employee_id = ?
                        """,
                        (full_name, employee_id)
                    )
                    row = await cur.fetchone()
            await pool.close()
            if row:
                department, position = row
                return {
                    "verified": True,
                    "department": department or "",
                    "position": position or "",
                    "employee_id": employee_id
                }
            return {"verified": False}
        except Exception as e:
            logger.error(f"MSSQL verify_employee error: {e}")
            return {"verified": False, "error": str(e)}
    
    # MySQL
    if _mysql_enabled():
        try:
            pool = await _mysql_get_pool()
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        """
                        SELECT department, position FROM employees
                        WHERE full_name = %s AND employee_id = %s
                        LIMIT 1
                        """,
                        (full_name, employee_id)
                    )
                    row = await cur.fetchone()
            await pool.wait_closed()
            if row:
                department, position = row
                return {
                    "verified": True,
                    "department": department or "",
                    "position": position or "",
                    "employee_id": employee_id
                }
            return {"verified": False}
        except Exception as e:
            logger.error(f"MySQL verify_employee error: {e}")
            return {"verified": False, "error": str(e)}

    # SQLite fallback
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
        logger.error(f"SQLite verify_employee error: {e}")
        return {"verified": False, "error": str(e)}

async def log_registration_attempt(telegram_id: int, full_name: str, employee_id: str, success: bool):
    """Логирование попытки регистрации (SQLite)."""
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
    """Получение истории попыток регистрации (SQLite)."""
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

async def get_all_employees() -> list:
    """Список сотрудников: MSSQL -> MySQL -> SQLite."""
    # MSSQL
    if _mssql_enabled():
        try:
            pool = await _mssql_get_pool()
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("SELECT employee_id, full_name, department, position FROM employees")
                    rows = await cur.fetchall()
            await pool.close()
            return [
                {
                    "employee_id": r[0],
                    "full_name": r[1],
                    "department": r[2],
                    "position": r[3],
                }
                for r in (rows or [])
            ]
        except Exception as e:
            logger.error(f"MSSQL get_all_employees error: {e}")
            return []

    # MySQL
    if _mysql_enabled():
        try:
            import aiomysql
            pool = await _mysql_get_pool()
            async with pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:  # type: ignore
                    await cur.execute("SELECT employee_id, full_name, department, position FROM employees")
                    rows = await cur.fetchall()
            await pool.wait_closed()
            return rows or []
        except Exception as e:
            logger.error(f"MySQL get_all_employees error: {e}")
            return []

    # SQLite fallback
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM employees") as cursor:
                employees = await cursor.fetchall()
                return [dict(emp) for emp in employees]
    except Exception as e:
        logger.error(f"SQLite get_all_employees error: {e}")
        return [] 