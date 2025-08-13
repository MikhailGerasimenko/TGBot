import logging
from aiogram import Bot, types, Dispatcher
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
import os
import asyncio
from typing import List, Dict, Optional, Set
from datetime import datetime, timedelta
from database import verify_employee, log_registration_attempt, get_registration_attempts, get_all_employees
from llm_client import LLMClient
import numpy as np
from docx import Document
import re
from collections import defaultdict
from config import API_TOKEN, ADMIN_CHAT_ID, DOCS_DIR as DOCUMENTS_DIR, LOGS_DIR, ONEC_EXPORT_PATH
from onec_sync import load_employees_from_file

# Конфигурация для LLM (через сервис)
MAX_LENGTH = 2048
MAX_NEW_TOKENS = 512

# Глобальные переменные для клиентов
llm_client = LLMClient()

auth_logger = logging.getLogger(__name__)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOGS_DIR, 'bot.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Инициализация бота
bot = Bot(token=API_TOKEN)

# Клавиатуры
main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text='/help'), KeyboardButton(text='/ask')],
    ],
    resize_keyboard=True
)
retry_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text='повтор')], [KeyboardButton(text='/cancel')]],
    resize_keyboard=True
)

# Вспомогательные: отправка администратору
async def send_admin_notification(text: str) -> bool:
    try:
        await bot.send_message(ADMIN_CHAT_ID, text, parse_mode='HTML')
        return True
    except Exception as e:
        logger.error(f"Ошибка отправки уведомления администратору: {e}")
        return False

# Нормализация ввода и данных
DASHES = "\u2010\u2011\u2012\u2013\u2014\u2212\uFE58\uFE63\uFF0D"
DASH_TRANS = str.maketrans({c: '-' for c in DASHES})

def normalize_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())

def normalize_name(text: str) -> str:
    return normalize_spaces(text).lower()

def normalize_employee_id(text: str) -> str:
    t = (text or "").translate(DASH_TRANS)
    t = t.replace(' ', '')  # убираем случайные пробелы внутри
    return t.upper()

# ========== ДАННЫЕ И СОСТОЯНИЯ (без Redis) ==========

# Кэш сотрудников в памяти (employee_id -> dict)
EMPLOYEES_CACHE: Dict[str, dict] = {}
# Индекс по нормализованному ID
EMPLOYEES_BY_NORM_ID: Dict[str, dict] = {}

# Попытки регистрации и состояния пользователей
REGISTRATION_ATTEMPTS: Dict[int, Dict[str, any]] = {}
MAX_ATTEMPTS = 3
RETRY_COMMANDS = ['retry', 'повтор', 'заново']
USER_STATES: Dict[int, Dict[str, any]] = {}
AUTHORIZED_USERS: Set[int] = set()
AUTHORIZED_INFO: Dict[int, Dict[str, str]] = {}

async def set_user_state(user_id: int, key: str, value: str):
    state = USER_STATES.get(user_id, {})
    state[key] = value
    USER_STATES[user_id] = state

async def get_user_state(user_id: int, key: str) -> Optional[str]:
    return USER_STATES.get(user_id, {}).get(key)

async def clear_user_state(user_id: int):
    if user_id in USER_STATES:
        del USER_STATES[user_id]

async def can_try_registration(user_id: int) -> bool:
    now_key = datetime.now().strftime('%Y%m%d')
    data = REGISTRATION_ATTEMPTS.get(user_id)
    if not data or data.get('date') != now_key:
        return True
    return data.get('count', 0) < MAX_ATTEMPTS

async def inc_registration_attempt(user_id: int):
    now_key = datetime.now().strftime('%Y%m%d')
    data = REGISTRATION_ATTEMPTS.get(user_id)
    if not data or data.get('date') != now_key:
        REGISTRATION_ATTEMPTS[user_id] = {'date': now_key, 'count': 1}
    else:
        data['count'] = data.get('count', 0) + 1
        REGISTRATION_ATTEMPTS[user_id] = data

async def get_next_attempt_time(user_id: int) -> str:
    data = REGISTRATION_ATTEMPTS.get(user_id)
    if not data:
        return "сейчас"
    # Следующий день в 00:00
    next_day = datetime.strptime(data['date'], '%Y%m%d') + timedelta(days=1)
    return next_day.strftime('%d.%m.%Y в %H:%M')

async def load_employees_from_file_to_cache() -> int:
    if not ONEC_EXPORT_PATH:
        return 0
    try:
        rows = await load_employees_from_file(ONEC_EXPORT_PATH)
        EMPLOYEES_CACHE.clear()
        EMPLOYEES_BY_NORM_ID.clear()
        for emp in rows:
            emp_id = emp['employee_id']
            EMPLOYEES_CACHE[emp_id] = emp
            norm = normalize_employee_id(emp_id)
            emp['norm_id'] = norm
            emp['norm_name'] = normalize_name(emp.get('full_name', ''))
            EMPLOYEES_BY_NORM_ID[norm] = emp
        logger.info(f"Импортировано из файла: {len(rows)} записей")
        return len(rows)
    except Exception as e:
        logger.error(f"Ошибка загрузки сотрудников из файла: {e}")
        return 0

# Обновляем IC_CACHE для работы с локальной БД/файлом
IC_CACHE = {
    "last_sync": None,
    "sync_in_progress": False
}

# ========== СИНХРОНИЗАЦИЯ ==========

async def sync_with_1c():
    """Синхронизация данных сотрудников: приоритет файл, затем БД."""
    if IC_CACHE["sync_in_progress"]:
        return False
    try:
        IC_CACHE["sync_in_progress"] = True
        success = False
        if ONEC_EXPORT_PATH:
            cnt = await load_employees_from_file_to_cache()
            success = cnt > 0
        else:
            employees = await get_all_employees()
            EMPLOYEES_CACHE.clear()
            EMPLOYEES_BY_NORM_ID.clear()
            for emp in employees:
                EMPLOYEES_CACHE[emp["employee_id"]] = emp
                norm = normalize_employee_id(emp["employee_id"])
                emp['norm_id'] = norm
                emp['norm_name'] = normalize_name(emp.get('full_name', ''))
                EMPLOYEES_BY_NORM_ID[norm] = emp
            success = len(EMPLOYEES_CACHE) > 0
        if success:
            IC_CACHE["last_sync"] = datetime.now()
            logger.info("Successfully synced employees (memory cache)")
            return True
        return False
    except Exception as e:
        logger.error(f"Error syncing employees: {e}")
        return False
    finally:
        IC_CACHE["sync_in_progress"] = False

async def periodic_sync():
    """Периодическая синхронизация сотрудниов из файла/БД"""
    while True:
        try:
            if (not IC_CACHE["last_sync"] or 
                datetime.now() - IC_CACHE["last_sync"] > timedelta(hours=1)):
                logger.info("Запуск периодической синхронизации")
                success = await sync_with_1c()
                if success:
                    await send_admin_notification(
                        f"✅ Синхронизация выполнена\n"
                        f"🕒 Время: {IC_CACHE['last_sync'].strftime('%Y-%m-%d %H:%M:%S')}"
                    )
                    await asyncio.sleep(3600)
                else:
                    await asyncio.sleep(300)
            else:
                await asyncio.sleep(60)
        except Exception as e:
            logger.error(f"Ошибка в periodic_sync: {e}")
            await asyncio.sleep(300)

async def verify_user_in_1c(full_name: str, employee_id: str) -> Optional[dict]:
    """Проверка пользователя по кэшу из файла (приоритет) или БД."""
    try:
        if not IC_CACHE["last_sync"] or datetime.now() - IC_CACHE["last_sync"] > timedelta(hours=1):
            await sync_with_1c()
        norm_id = normalize_employee_id(employee_id)
        norm_name = normalize_name(full_name)
        emp = EMPLOYEES_BY_NORM_ID.get(norm_id)
        if emp and emp.get('norm_name') == norm_name:
            return {
                "verified": True,
                "department": emp.get("department", ""),
                "position": emp.get("position", ""),
                "employee_id": emp.get("employee_id", employee_id),
                "from_cache": True
            }
        # Фоллбек на БД
        result = await verify_employee(full_name, employee_id)
        logger.info(f"Employee verification result for {full_name} (ID: {employee_id}): {result}")
        return result
    except Exception as e:
        logger.error(f"Employee verification error: {e}")
        return None

# ========== ФУНКЦИИ ДЛЯ РАБОТЫ С ДОКУМЕНТАМИ ==========

def extract_text_from_docx(file_path: str) -> str:
    try:
        doc = Document(file_path)
        full_text = []
        for para in doc.paragraphs:
            text = re.sub(r'\s+', ' ', para.text.strip())
            if text:
                full_text.append(text)
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    text = re.sub(r'\s+', ' ', cell.text.strip())
                    if text:
                        full_text.append(text)
        return '\n'.join(full_text)
    except Exception as e:
        logger.error(f"Ошибка при чтении документа: {e}")
        return ""

def split_text_into_chunks(text: str, chunk_size: int = 500) -> List[str]:
    sentences = text.split('.')
    chunks = []
    current_chunk = []
    current_length = 0
    for sentence in sentences:
        sentence = sentence.strip() + '.'
        sentence_length = len(sentence.split())
        if current_length + sentence_length > chunk_size:
            if current_chunk:
                chunks.append(' '.join(current_chunk))
            current_chunk = [sentence]
            current_length = sentence_length
        else:
            current_chunk.append(sentence)
            current_length += sentence_length
    if current_chunk:
        chunks.append(' '.join(current_chunk))
    return chunks

async def index_document(file_path: str) -> bool:
    global document_embeddings, document_chunks
    try:
        text = extract_text_from_docx(file_path)
        if not text:
            return False
        chunks = split_text_into_chunks(text)
        embeddings = await llm_client.create_embeddings(chunks)
        if embeddings is None:
            return False
        embeddings = np.array(embeddings)
        document_chunks.extend(chunks)
        if document_embeddings is None:
            document_embeddings = embeddings
        else:
            document_embeddings = np.vstack([document_embeddings, embeddings])
        logger.info(f"Документ {file_path} успешно проиндексирован")
        return True
    except Exception as e:
        logger.error(f"Ошибка при индексации документа: {e}")
        return False

async def awaitable_create_query_embedding(query: str):
    try:
        return await llm_client.create_embeddings([query])
    except Exception:
        return None

def find_relevant_chunks(query: str, top_k: int = 3) -> List[str]:
    if not document_embeddings is None and len(document_chunks) > 0:
        try:
            loop = asyncio.get_event_loop()
            query_embedding_list = loop.run_until_complete(awaitable_create_query_embedding(query))
            if query_embedding_list is None:
                return []
            query_embedding = np.array(query_embedding_list[0])
            similarities = np.dot(document_embeddings, query_embedding)
            top_indices = np.argsort(similarities)[-top_k:][::-1]
            return [document_chunks[i] for i in top_indices]
        except Exception as e:
            logger.error(f"Ошибка при поиске релевантных чанков: {e}")
    return []

async def generate_response(query: str, context: str = "") -> str:
    try:
        response = await llm_client.generate(query=query, context=context, max_tokens=MAX_NEW_TOKENS)
        if response is None:
            return "Извините, произошла ошибка при обработке вашего запроса."
        return response
    except Exception as e:
        logger.error(f"Ошибка при генерации ответа: {e}")
        return "Извините, произошла ошибка при обработке вашего запроса."

# Глобальные переменные для RAG
document_embeddings = None
document_chunks = []

# ========== ОБРАБОТЧИКИ КОМАНД ==========

def setup_handlers(dp: Dispatcher):
    @dp.message(Command('start'))
    async def start_handler(message: types.Message):
        user_id = message.from_user.id
        if not API_TOKEN:
            await message.answer('❌ Не задан API_TOKEN. Укажите его в .env')
            return
        if user_id in AUTHORIZED_USERS:
            await message.answer('Добро пожаловать! Вы авторизованы.', reply_markup=main_kb)
            return
        if await can_try_registration(user_id):
            await set_user_state(user_id, 'step', 'name')
            await message.answer(
                'Для регистрации введите ваше ФИО\n'
                '(как указано в 1С, например: Иванов Иван Иванович)'
            )
        else:
            next_attempt = await get_next_attempt_time(user_id)
            await message.answer(
                f"⚠️ Превышено количество попыток регистрации.\n"
                f"Следующая попытка будет доступна {next_attempt}.\n\n"
                f"Если вам нужна помощь, обратитесь к администратору.",
                reply_markup=ReplyKeyboardRemove()
            )

    @dp.message(Command('cancel'))
    async def cancel_handler(message: types.Message):
        user_id = message.from_user.id
        await clear_user_state(user_id)
        await message.answer('Операция отменена. Используйте /start для регистрации.', reply_markup=ReplyKeyboardRemove())

    @dp.message(Command('status'))
    async def status_handler(message: types.Message):
        user_id = message.from_user.id
        if user_id not in AUTHORIZED_USERS:
            await message.answer('❌ Недоступно до завершения регистрации. Используйте /start.')
            return
        info = AUTHORIZED_INFO.get(user_id, {})
        await message.answer(
            f"👤 ФИО: {info.get('name','-')}\n"
            f"🔢 Табельный: {info.get('employee_id','-')}\n"
            f"🕒 Регистрация: {info.get('verified_at','-')}",
            reply_markup=main_kb
        )

    @dp.message(lambda message: message.text and message.text.lower() in RETRY_COMMANDS)
    async def retry_registration(message: types.Message):
        user_id = message.from_user.id
        if user_id in AUTHORIZED_USERS:
            await message.answer('Вы уже зарегистрированы.', reply_markup=main_kb)
            return
        if await can_try_registration(user_id):
            await clear_user_state(user_id)
            await set_user_state(user_id, 'step', 'name')
            await message.answer(
                "🔄 Начинаем регистрацию заново!\n\n"
                "Введите ваше ФИО\n"
                "(как указано в 1С, например: Иванов Иван Иванович)",
                reply_markup=ReplyKeyboardRemove()
            )
        else:
            next_attempt = await get_next_attempt_time(user_id)
            await message.answer(
                f"⚠️ Превышено количество попыток регистрации.\n"
                f"Следующая попытка будет доступна {next_attempt}.\n\n"
                f"Если вам нужна помощь, обратитесь к администратору.",
                reply_markup=ReplyKeyboardRemove()
            )

    @dp.message(lambda message: True)
    async def registration_handler(message: types.Message):
        user_id = message.from_user.id
        step = await get_user_state(user_id, 'step')
        if not step:
            return
        if step == 'name':
            name_parts = message.text.strip().split()
            if len(name_parts) != 3:
                await message.answer(
                    '❌ Пожалуйста, введите ФИО полностью\n'
                    'Формат: Фамилия Имя Отчество\n'
                    'Пример: Иванов Иван Иванович\n\n'
                    'Для повторной попытки напишите "повтор"'
                )
                return
            await set_user_state(user_id, 'name', message.text.strip())
            await set_user_state(user_id, 'step', 'employee_id')
            await message.answer(
                'Введите ваш табельный номер\n'
                '(как указано в 1С, например: E001)'
            )
        elif step == 'employee_id':
            employee_id = message.text.strip()
            name = await get_user_state(user_id, 'name')
            await set_user_state(user_id, 'employee_id', employee_id)
            verification_result = await verify_user_in_1c(name, employee_id)
            if verification_result and verification_result.get('verified'):
                await clear_user_state(user_id)
                AUTHORIZED_USERS.add(user_id)
                AUTHORIZED_INFO[user_id] = {
                    'name': name,
                    'employee_id': employee_id,
                    'department': verification_result.get('department',''),
                    'position': verification_result.get('position',''),
                    'verified_at': datetime.now().strftime('%Y-%m-%d %H:%M')
                }
                await log_registration_attempt(user_id, name, employee_id, True)
                await message.answer(
                    f"✅ Регистрация подтверждена!\n\n"
                    f"📋 Ваши данные:\n"
                    f"👤 ФИО: {name}\n"
                    f"🔢 Табельный номер: {employee_id}\n"
                    f"📝 Должность: {verification_result.get('position', 'Не указана')}\n"
                    f"🏢 Отдел: {verification_result.get('department', 'Не указан')}\n\n"
                    f"Теперь вам доступны команды /ask и /help.",
                    reply_markup=main_kb
                )
                # Приветственное сообщение
                welcome_text = (
                    "Привет! Я бот‑помощник вашей компании.\n\n"
                    "Что я умею:\n"
                    "• Отвечать на вопросы по внутренним процессам и документам — используйте команду /ask.\n"
                    "• Работать с предоставленной документацией (RAG), чтобы находить нужные фрагменты.\n"
                    "• Показывать ваш профиль через /status.\n\n"
                    "Как задать вопрос:\n"
                    "1) Нажмите /ask.\n"
                    "2) Одним сообщением опишите задачу или вопрос.\n"
                    "3) Я пришлю ответ и, при необходимости, уточню детали.\n\n"
                    "Полезно знать:\n"
                    "• Команда /help — краткая справка по доступным командам.\n"
                    "• Команда /cancel — отмена текущей операции.\n"
                    "• Если что‑то не получается — напишите администратору.\n\n"
                    "Хорошей работы!"
                )
                await message.answer(welcome_text, reply_markup=main_kb)
                await send_admin_notification(
                    f"✅ Новый пользователь зарегистрирован\n\n"
                    f"👤 {name}\n"
                    f"🔢 Табельный: {employee_id}\n"
                    f"📋 {verification_result.get('position', 'Не указана')}\n"
                    f"🏢 {verification_result.get('department', 'Не указан')}"
                )
            else:
                await inc_registration_attempt(user_id)
                await log_registration_attempt(user_id, name or '', employee_id, False)
                attempts = REGISTRATION_ATTEMPTS.get(user_id, {}).get('count', 0)
                attempts_left = MAX_ATTEMPTS - attempts
                error_msg = [
                    "❌ Ошибка проверки данных\n",
                    "Возможные причины:",
                    "1. Неверно указано ФИО",
                    "2. Неверный табельный номер",
                    "3. Данные не совпадают с базой\n"
                ]
                if attempts_left > 0:
                    error_msg.append(f"У вас осталось попыток: {attempts_left}")
                    error_msg.append("Для повторной попытки нажмите кнопку 'повтор' или /cancel")
                else:
                    next_attempt = await get_next_attempt_time(user_id)
                    error_msg.append(f"Следующая попытка будет доступна {next_attempt}")
                await message.answer('\n'.join(error_msg), reply_markup=retry_kb)
                await clear_user_state(user_id)
                await send_admin_notification(
                    f"⚠️ Неудачная попытка регистрации\n\n"
                    f"👤 Введено ФИО: {name or ''}\n"
                    f"🔢 Табельный: {employee_id}\n"
                    f"🆔 Telegram ID: {user_id}\n"
                    f"📊 Попытка: {attempts}/{MAX_ATTEMPTS}"
                )

    @dp.message(Command('ask'))
    async def ask_handler(message: types.Message):
        user_id = message.from_user.id
        if user_id not in AUTHORIZED_USERS:
            await message.answer("❌ Вы не авторизованы! Используйте /start для регистрации.")
            return
        awaiting = await get_user_state(user_id, 'awaiting_question')
        if not awaiting:
            await set_user_state(user_id, 'awaiting_question', '1')
        await message.answer(
            "Задайте ваш вопрос. Я постараюсь ответить, используя доступную документацию.",
            reply_markup=ReplyKeyboardRemove()
        )

    @dp.message(lambda message: True)
    async def process_question(message: types.Message):
        user_id = message.from_user.id
        if user_id not in AUTHORIZED_USERS:
            return
        awaiting = await get_user_state(user_id, 'awaiting_question')
        if not awaiting:
            return
        await set_user_state(user_id, 'awaiting_question', '0')
        processing_msg = await message.answer("🤔 Обрабатываю ваш вопрос...")
        try:
            # Гибридный поиск через сервис (при наличии индекса)
            import aiohttp
            top_context = ""
            sources_block = ""
            conf_threshold = 0.12
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(f"{llm_client.base_url}/search", json={"query": message.text, "top_k": 3}) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            hits = data.get('hits', [])
                            if hits:
                                top_context = "\n\n".join(h['text'] for h in hits)
                                sources_block = "\n\nИсточники:\n" + "\n".join([f"— {round(h['score'],3)}" for h in hits])
                                top_score = hits[0]['score']
                                if top_score < conf_threshold:
                                    await processing_msg.edit_text(
                                        "Я не уверен в ответе. Уточните вопрос или добавьте деталей (дата, подразделение, документ)."
                                    )
                                    return
            except Exception:
                pass

            # Генерация
            context = top_context
            response = await generate_response(message.text, context)
            await processing_msg.edit_text(
                f"Вопрос: {message.text}\n\n"
                f"Ответ: {response}{sources_block}",
                reply_markup=main_kb
            )
        except Exception as e:
            logger.error(f"Ошибка при обработке вопроса: {e}")
            await processing_msg.edit_text(
                "😔 Извините, произошла ошибка при обработке вашего вопроса. Попробуйте позже.",
                reply_markup=main_kb
            )

    @dp.message(Command('sources'))
    async def sources_handler(message: types.Message):
        await message.answer("Команда покажет источники после ответа, когда они есть в выдаче поиска.")

    @dp.message(Command('train'))
    async def train_handler(message: types.Message):
        """Обработчик команды для добавления документов"""
        if message.from_user.id != ADMIN_CHAT_ID:
            await message.answer("❌ Эта команда доступна только администратору.")
            return
        
        USER_STATES[message.from_user.id] = {"awaiting_document": True}
        await message.answer(
            "📄 Отправьте документ в формате .docx для обучения.",
            reply_markup=ReplyKeyboardRemove()
        )
    
    @dp.message(lambda m: m.document and m.document.file_name.endswith('.docx'))
    async def process_document(message: types.Message):
        """Обработка загруженного документа"""
        if message.from_user.id != ADMIN_CHAT_ID or \
           message.from_user.id not in USER_STATES or \
           not USER_STATES[message.from_user.id].get("awaiting_document"):
            return
        
        USER_STATES[message.from_user.id]["awaiting_document"] = False
        processing_msg = await message.answer("📥 Загрузка документа...")
        
        try:
            # Создаем директорию если нет
            os.makedirs(DOCUMENTS_DIR, exist_ok=True)
            
            # Сохраняем документ
            file_path = os.path.join(DOCUMENTS_DIR, message.document.file_name)
            await bot.download(
                message.document,
                destination=file_path
            )
            
            # Индексируем документ локально для RAG
            ok_local = await index_document(file_path)

            # Отправляем текст в сервис для гибридного поиска
            text = extract_text_from_docx(file_path)
            ok_remote = False
            if text:
                try:
                    import aiohttp
                    async with aiohttp.ClientSession() as session:
                        async with session.post(f"{llm_client.base_url}/index", json={"documents": [text]}) as resp:
                            ok_remote = (resp.status == 200)
                except Exception:
                    ok_remote = False

            if ok_local:
                await processing_msg.edit_text(
                    "✅ Документ успешно загружен и проиндексирован!",
                    reply_markup=main_kb
                )
            else:
                await processing_msg.edit_text(
                    "❌ Не удалось проиндексировать документ.",
                    reply_markup=main_kb
                )
        except Exception as e:
            logger.error(f"Ошибка при обработке документа: {e}")
            await processing_msg.edit_text(
                "❌ Произошла ошибка при обработке документа.",
                reply_markup=main_kb
            )
    
    @dp.message(Command('help'))
    async def help_handler(message: types.Message):
        if message.from_user.id not in AUTHORIZED_USERS:
            await message.answer("❌ Недоступно до завершения регистрации. Используйте /start.")
            return
        help_text = (
            '<b>Доступные команды:</b>\n\n'
            '/start - начать регистрацию\n'
            '/status - показать профиль\n'
            '/ask - задать вопрос ассистенту\n'
            '/cancel - отменить текущую операцию\n'
            "'повтор' - повторить попытку регистрации\n"
            '/help - помощь'
        )
        if message.from_user.id == ADMIN_CHAT_ID:
            help_text += '\n\n<b>Админ-команды:</b>\n' \
                        '/train - добавить документ для обучения\n' \
                        '/stats - статистика регистраций'
        await message.answer(help_text, parse_mode='HTML', reply_markup=main_kb)