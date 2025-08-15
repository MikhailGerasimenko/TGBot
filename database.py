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

CREATE TABLE IF NOT EXISTS qa_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER NOT NULL,
    user_name TEXT,
    employee_id TEXT,
    question TEXT NOT NULL,
    answer TEXT,
    response_time_ms INTEGER,
    confidence_score REAL,
    context_found BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    qa_session_id INTEGER,
    telegram_id INTEGER NOT NULL,
    rating INTEGER CHECK(rating IN (1, -1)),
    comment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (qa_session_id) REFERENCES qa_sessions (id)
);

CREATE TABLE IF NOT EXISTS unanswered_questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER NOT NULL,
    question TEXT NOT NULL,
    user_context TEXT,
    frequency INTEGER DEFAULT 1,
    last_asked TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved BOOLEAN DEFAULT FALSE
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

# ========== АНАЛИТИКА И МЕТРИКИ ==========

async def log_qa_session(telegram_id: int, user_name: str, employee_id: str, 
                        question: str, answer: str, response_time_ms: int, 
                        confidence_score: float = None, context_found: bool = False) -> int:
    """Логирование сессии Q&A. Возвращает ID сессии."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                """INSERT INTO qa_sessions 
                (telegram_id, user_name, employee_id, question, answer, response_time_ms, confidence_score, context_found)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (telegram_id, user_name, employee_id, question, answer, response_time_ms, confidence_score, context_found)
            )
            await db.commit()
            return cursor.lastrowid
    except Exception as e:
        logger.error(f"Ошибка при логировании QA сессии: {e}")
        return 0

async def save_feedback(qa_session_id: int, telegram_id: int, rating: int, comment: str = None) -> bool:
    """Сохранение фидбека пользователя (1 = лайк, -1 = дизлайк)."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                """INSERT INTO feedback (qa_session_id, telegram_id, rating, comment)
                VALUES (?, ?, ?, ?)""",
                (qa_session_id, telegram_id, rating, comment)
            )
            await db.commit()
        return True
    except Exception as e:
        logger.error(f"Ошибка при сохранении фидбека: {e}")
        return False

async def log_unanswered_question(telegram_id: int, question: str, user_context: str = "") -> bool:
    """Логирование неотвеченного вопроса с увеличением частоты при повторе."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # Проверяем, есть ли уже такой вопрос
            async with db.execute(
                "SELECT id, frequency FROM unanswered_questions WHERE question = ? AND resolved = FALSE",
                (question,)
            ) as cursor:
                existing = await cursor.fetchone()
            
            if existing:
                # Увеличиваем частоту
                await db.execute(
                    "UPDATE unanswered_questions SET frequency = frequency + 1, last_asked = CURRENT_TIMESTAMP WHERE id = ?",
                    (existing[0],)
                )
            else:
                # Добавляем новый
                await db.execute(
                    "INSERT INTO unanswered_questions (telegram_id, question, user_context) VALUES (?, ?, ?)",
                    (telegram_id, question, user_context)
                )
            await db.commit()
        return True
    except Exception as e:
        logger.error(f"Ошибка при логировании неотвеченного вопроса: {e}")
        return False

async def get_analytics_stats(days: int = 7) -> dict:
    """Получение статистики за последние N дней."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            stats = {}
            
            # Общая статистика Q&A
            async with db.execute(
                """SELECT 
                    COUNT(*) as total_questions,
                    AVG(response_time_ms) as avg_response_time,
                    AVG(confidence_score) as avg_confidence,
                    SUM(CASE WHEN context_found = 1 THEN 1 ELSE 0 END) as questions_with_context
                FROM qa_sessions 
                WHERE created_at >= datetime('now', '-{} days')""".format(days)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    stats['total_questions'] = row[0]
                    stats['avg_response_time_ms'] = round(row[1] or 0)
                    stats['avg_confidence'] = round(row[2] or 0, 3)
                    stats['questions_with_context'] = row[3]
            
            # Топ вопросов
            async with db.execute(
                """SELECT question, COUNT(*) as frequency 
                FROM qa_sessions 
                WHERE created_at >= datetime('now', '-{} days')
                GROUP BY question 
                ORDER BY frequency DESC 
                LIMIT 5""".format(days)
            ) as cursor:
                stats['top_questions'] = await cursor.fetchall()
            
            # Фидбек
            async with db.execute(
                """SELECT 
                    SUM(CASE WHEN rating = 1 THEN 1 ELSE 0 END) as likes,
                    SUM(CASE WHEN rating = -1 THEN 1 ELSE 0 END) as dislikes
                FROM feedback f
                JOIN qa_sessions qa ON f.qa_session_id = qa.id
                WHERE qa.created_at >= datetime('now', '-{} days')""".format(days)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    stats['likes'] = row[0] or 0
                    stats['dislikes'] = row[1] or 0
                    total_feedback = stats['likes'] + stats['dislikes']
                    stats['satisfaction_rate'] = round(stats['likes'] / total_feedback * 100, 1) if total_feedback > 0 else 0
            
            # Неотвеченные вопросы
            async with db.execute(
                """SELECT question, frequency 
                FROM unanswered_questions 
                WHERE resolved = FALSE 
                ORDER BY frequency DESC, last_asked DESC 
                LIMIT 10"""
            ) as cursor:
                stats['unanswered_questions'] = await cursor.fetchall()
            
            return stats
    except Exception as e:
        logger.error(f"Ошибка при получении статистики: {e}")
        return {}

async def get_popular_questions(limit: int = 10, days: int = 30) -> list:
    """Получение самых популярных вопросов за период."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                """SELECT question, COUNT(*) as frequency, AVG(confidence_score) as avg_confidence
                FROM qa_sessions 
                WHERE created_at >= datetime('now', '-{} days')
                GROUP BY question 
                ORDER BY frequency DESC 
                LIMIT ?""".format(days),
                (limit,)
            ) as cursor:
                return await cursor.fetchall()
    except Exception as e:
        logger.error(f"Ошибка при получении популярных вопросов: {e}")
        return [] 