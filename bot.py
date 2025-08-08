import logging
from aiogram import Bot, types, Dispatcher
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
import os
import asyncio
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from database import verify_employee, log_registration_attempt, get_registration_attempts, get_all_employees
from llm_client import LLMClient
import numpy as np
from docx import Document
import re
from collections import defaultdict
from config import API_TOKEN, ADMIN_CHAT_ID, DOCS_DIR as DOCUMENTS_DIR, LOGS_DIR

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

# Клавиатура
main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text='/help'), KeyboardButton(text='/ask')],
    ],
    resize_keyboard=True
)

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========

async def send_admin_notification(text: str) -> bool:
    """Отправка уведомления администратору"""
    try:
        await bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=text,
            parse_mode='HTML'
        )
        return True
    except Exception as e:
        logger.error(f"Ошибка отправки уведомления: {e}")
        return False

# Обновляем IC_CACHE для работы с локальной БД
IC_CACHE = {
    "employees": {},
    "last_sync": None,
    "sync_in_progress": False
}

# Данные пользователей
AUTHORIZED_USERS = {}
PENDING_REGISTRATIONS = {}  # user_id -> {step, name, employee_id, ...}

# Добавляем структуру для отслеживания попыток регистрации
REGISTRATION_ATTEMPTS = {}  # user_id -> {attempts: int, last_attempt: datetime}
MAX_ATTEMPTS = 3  # Максимальное количество попыток в течение дня
RETRY_COMMANDS = ['retry', 'повтор', 'заново']

# Состояния пользователей
USER_STATES = {}

async def sync_with_1c():
    """Синхронизация данных с локальной БД"""
    if IC_CACHE["sync_in_progress"]:
        return False
        
    try:
        IC_CACHE["sync_in_progress"] = True
        employees = await get_all_employees()
        
        # Обновляем кэш
        IC_CACHE["employees"] = {
            emp["employee_id"]: emp for emp in employees
        }
        IC_CACHE["last_sync"] = datetime.now()
        logger.info("Successfully synced with local database")
        return True
        
    except Exception as e:
        logger.error(f"Error syncing with local database: {e}")
        return False
    finally:
        IC_CACHE["sync_in_progress"] = False

async def periodic_sync():
    """Периодическая синхронизация с БД"""
    while True:
        try:
            # Проверяем, нужна ли синхронизация
            if (not IC_CACHE["last_sync"] or 
                datetime.now() - IC_CACHE["last_sync"] > timedelta(hours=1)):
                
                logger.info("Запуск периодической синхронизации")
                success = await sync_with_1c()
                
                if success:
                    # Уведомляем админа о успешной синхронизации
                    await send_admin_notification(
                        f"✅ Синхронизация выполнена\n"
                        f"📊 Сотрудников в кэше: {len(IC_CACHE['employees'])}\n"
                        f"🕒 Время: {IC_CACHE['last_sync'].strftime('%Y-%m-%d %H:%M:%S')}"
                    )
                    # Ждем до следующей синхронизации
                    await asyncio.sleep(3600)  # 1 час
                else:
                    # В случае ошибки ждем меньше
                    await asyncio.sleep(300)  # 5 минут
            else:
                await asyncio.sleep(60)  # Проверяем каждую минуту
                
        except Exception as e:
            logger.error(f"Ошибка в periodic_sync: {e}")
            await asyncio.sleep(300)

async def verify_user_in_1c(full_name: str, employee_id: str) -> Optional[dict]:
    """Проверка пользователя в локальной базе данных"""
    try:
        # Проверяем актуальность кэша
        if not IC_CACHE["last_sync"] or datetime.now() - IC_CACHE["last_sync"] > timedelta(hours=1):
            await sync_with_1c()
        
        # Сначала проверяем в кэше
        for emp in IC_CACHE["employees"].values():
            if (emp["full_name"].lower() == full_name.lower() and 
                emp["employee_id"] == employee_id):
                return {
                    "verified": True,
                    "department": emp.get("department", ""),
                    "position": emp.get("position", ""),
                    "employee_id": employee_id,
                    "from_cache": True
                }
        
        # Если нет в кэше, проверяем через БД
        result = await verify_employee(full_name, employee_id)
        logger.info(f"Employee verification result for {full_name} (ID: {employee_id}): {result}")
        return result
        
    except Exception as e:
        logger.error(f"Employee verification error: {e}")
        return None

def can_try_registration(user_id: int) -> bool:
    """Проверка возможности попытки регистрации"""
    if user_id not in REGISTRATION_ATTEMPTS:
        return True
        
    attempts = REGISTRATION_ATTEMPTS[user_id]
    now = datetime.now()
    
    # Сбрасываем счетчик, если прошел день
    if (now - attempts['last_attempt']).days >= 1:
        attempts['attempts'] = 0
        return True
    
    return attempts['attempts'] < MAX_ATTEMPTS

def get_next_attempt_time(user_id: int) -> str:
    """Получение времени следующей доступной попытки"""
    if user_id not in REGISTRATION_ATTEMPTS:
        return "сейчас"
        
    attempts = REGISTRATION_ATTEMPTS[user_id]
    next_time = attempts['last_attempt'] + timedelta(days=1)
    return next_time.strftime("%d.%m.%Y в %H:%M")

def update_registration_attempts(user_id: int):
    """Обновление счетчика попыток регистрации"""
    if user_id not in REGISTRATION_ATTEMPTS:
        REGISTRATION_ATTEMPTS[user_id] = {
            'attempts': 1,
            'last_attempt': datetime.now()
        }
    else:
        REGISTRATION_ATTEMPTS[user_id]['attempts'] += 1
        REGISTRATION_ATTEMPTS[user_id]['last_attempt'] = datetime.now()

# ========== ФУНКЦИИ ДЛЯ РАБОТЫ С ДОКУМЕНТАМИ ==========

def extract_text_from_docx(file_path: str) -> str:
    """Извлечение текста из Word файла"""
    try:
        doc = Document(file_path)
        full_text = []
        
        # Извлекаем текст из параграфов
        for para in doc.paragraphs:
            text = re.sub(r'\s+', ' ', para.text.strip())
            if text:
                full_text.append(text)
        
        # Извлекаем текст из таблиц
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
    """Разделение текста на чанки"""
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
    """Индексация документа (через сервис эмбеддингов)"""
    global document_embeddings, document_chunks
    
    try:
        # Извлекаем текст
        text = extract_text_from_docx(file_path)
        if not text:
            return False
            
        # Разбиваем на чанки
        chunks = split_text_into_chunks(text)
        
        # Создаем эмбеддинги через сервис
        embeddings = await llm_client.create_embeddings(chunks)
        if embeddings is None:
            return False
        embeddings = np.array(embeddings)
        
        # Сохраняем
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

def find_relevant_chunks(query: str, top_k: int = 3) -> List[str]:
    """Поиск релевантных чанков"""
    if not document_embeddings is None and len(document_chunks) > 0:
        try:
            # Получаем эмбеддинг запроса через сервис
            query_embedding_list = awaitable_create_query_embedding(query)
            if query_embedding_list is None:
                return []
            query_embedding = np.array(query_embedding_list[0])
            
            # Считаем косинусное сходство
            similarities = np.dot(document_embeddings, query_embedding)
            
            # Получаем топ-k чанков
            top_indices = np.argsort(similarities)[-top_k:][::-1]
            return [document_chunks[i] for i in top_indices]
        except Exception as e:
            logger.error(f"Ошибка при поиске релевантных чанков: {e}")
    
    return []

async def awaitable_create_query_embedding(query: str):
    try:
        return await llm_client.create_embeddings([query])
    except Exception:
        return None

async def generate_response(query: str, context: str = "") -> str:
    """Генерация ответа через сервис LLM"""
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
    """Регистрация всех обработчиков"""
    
    @dp.message(Command('start'))
    async def start_handler(message: types.Message):
        user_id = message.from_user.id
        if not API_TOKEN:
            await message.answer('❌ Не задан API_TOKEN. Укажите его в .env')
            return
        if user_id in AUTHORIZED_USERS:
            await message.answer('Добро пожаловать! Вы авторизованы.', reply_markup=main_kb)
        else:
            # Проверяем количество попыток
            if can_try_registration(user_id):
                PENDING_REGISTRATIONS[user_id] = {'step': 'name'}
                await message.answer(
                    'Для регистрации введите ваше ФИО\n'
                    '(как указано в 1С, например: Иванов Иван Иванович)'
                )
            else:
                # Если превышен лимит попыток
                next_attempt = get_next_attempt_time(user_id)
                await message.answer(
                    f"⚠️ Превышено количество попыток регистрации.\n"
                    f"Следующая попытка будет доступна {next_attempt}.\n\n"
                    f"Если вам нужна помощь, обратитесь к администратору."
                )

    @dp.message(lambda message: message.text and message.text.lower() in RETRY_COMMANDS)
    async def retry_registration(message: types.Message):
        """Обработчик команды повторной регистрации"""
        user_id = message.from_user.id
        
        if user_id in AUTHORIZED_USERS:
            await message.answer("Вы уже зарегистрированы!")
            return
            
        if can_try_registration(user_id):
            # Очищаем предыдущие данные регистрации
            if user_id in PENDING_REGISTRATIONS:
                del PENDING_REGISTRATIONS[user_id]
                
            # Начинаем новую регистрацию
            PENDING_REGISTRATIONS[user_id] = {'step': 'name'}
            await message.answer(
                "🔄 Начинаем регистрацию заново!\n\n"
                "Введите ваше ФИО\n"
                "(как указано в 1С, например: Иванов Иван Иванович)"
            )
        else:
            next_attempt = get_next_attempt_time(user_id)
            await message.answer(
                f"⚠️ Превышено количество попыток регистрации.\n"
                f"Следующая попытка будет доступна {next_attempt}.\n\n"
                f"Если вам нужна помощь, обратитесь к администратору."
            )

    @dp.message(lambda message: message.from_user.id in PENDING_REGISTRATIONS)
    async def registration_handler(message: types.Message):
        user_id = message.from_user.id
        reg_data = PENDING_REGISTRATIONS[user_id]
        
        if reg_data['step'] == 'name':
            # Проверяем формат ФИО (должно быть 3 слова)
            name_parts = message.text.strip().split()
            if len(name_parts) != 3:
                await message.answer(
                    '❌ Пожалуйста, введите ФИО полностью\n'
                    'Формат: Фамилия Имя Отчество\n'
                    'Пример: Иванов Иван Иванович\n\n'
                    'Для повторной попытки напишите "повтор"'
                )
                return
            
            reg_data['name'] = message.text.strip()
            reg_data['step'] = 'employee_id'
            await message.answer(
                'Введите ваш табельный номер\n'
                '(как указано в 1С, например: E001)'
            )
            
        elif reg_data['step'] == 'employee_id':
            employee_id = message.text.strip()
            reg_data['employee_id'] = employee_id
            
            # Проверка в БД
            verification_result = await verify_user_in_1c(reg_data['name'], employee_id)
            
            if verification_result and verification_result.get('verified'):
                # Пользователь найден
                AUTHORIZED_USERS[user_id] = {
                    'name': reg_data['name'],
                    'employee_id': employee_id,
                    'department': verification_result.get('department', ''),
                    'position': verification_result.get('position', ''),
                    'verified_at': datetime.now().isoformat()
                }
                del PENDING_REGISTRATIONS[user_id]
                
                # Очищаем историю попыток при успешной регистрации
                if user_id in REGISTRATION_ATTEMPTS:
                    del REGISTRATION_ATTEMPTS[user_id]
                
                # Логируем успешную попытку
                await log_registration_attempt(user_id, reg_data['name'], employee_id, True)
                
                await message.answer(
                    f"✅ Регистрация подтверждена!\n\n"
                    f"📋 Ваши данные:\n"
                    f"👤 ФИО: {reg_data['name']}\n"
                    f"🔢 Табельный номер: {employee_id}\n"
                    f"📝 Должность: {verification_result.get('position', 'Не указана')}\n"
                    f"🏢 Отдел: {verification_result.get('department', 'Не указан')}\n\n"
                    f"Теперь вам доступны все команды бота.",
                    reply_markup=main_kb
                )
                
                await send_admin_notification(
                    f"✅ Новый пользователь зарегистрирован\n\n"
                    f"👤 {reg_data['name']}\n"
                    f"🔢 Табельный: {employee_id}\n"
                    f"📋 {verification_result.get('position', 'Не указана')}\n"
                    f"🏢 {verification_result.get('department', 'Не указан')}"
                )
            else:
                # Обновляем счетчик попыток
                update_registration_attempts(user_id)
                
                # Логируем неуспешную попытку
                await log_registration_attempt(user_id, reg_data.get('name', ''), employee_id, False)
                
                # Формируем сообщение об ошибке
                error_msg = [
                    "❌ Ошибка проверки данных\n",
                    "Возможные причины:",
                    "1. Неверно указано ФИО",
                    "2. Неверный табельный номер",
                    "3. Данные не совпадают с базой\n"
                ]
                
                # Добавляем информацию о попытках
                attempts_left = MAX_ATTEMPTS - REGISTRATION_ATTEMPTS[user_id]['attempts']
                if attempts_left > 0:
                    error_msg.append(f"У вас осталось попыток: {attempts_left}")
                    error_msg.append("Для повторной попытки напишите 'повтор'")
                else:
                    next_attempt = get_next_attempt_time(user_id)
                    error_msg.append(f"Следующая попытка будет доступна {next_attempt}")
                
                await message.answer('\n'.join(error_msg))
                del PENDING_REGISTRATIONS[user_id]
                
                await send_admin_notification(
                    f"⚠️ Неудачная попытка регистрации\n\n"
                    f"👤 Введено ФИО: {reg_data.get('name', '')}\n"
                    f"🔢 Табельный: {employee_id}\n"
                    f"🆔 Telegram ID: {user_id}\n"
                    f"📊 Попытка: {REGISTRATION_ATTEMPTS[user_id]['attempts']}/{MAX_ATTEMPTS}"
                )

    @dp.message(Command('ask'))
    async def ask_handler(message: types.Message):
        """Обработчик команды запроса к LLM"""
        user_id = message.from_user.id
        
        if user_id not in AUTHORIZED_USERS:
            await message.answer("❌ Вы не авторизованы! Используйте /start для регистрации.")
            return
        
        USER_STATES[user_id] = {"awaiting_question": True}
        await message.answer(
            "Задайте ваш вопрос. Я постараюсь ответить, используя доступную документацию.",
            reply_markup=ReplyKeyboardRemove()
        )
    
    @dp.message(lambda message: message.from_user.id in USER_STATES and USER_STATES[message.from_user.id].get("awaiting_question"))
    async def process_question(message: types.Message):
        """Обработка вопроса пользователя"""
        user_id = message.from_user.id
        USER_STATES[user_id]["awaiting_question"] = False
        
        # Отправляем сообщение о начале обработки
        processing_msg = await message.answer("🤔 Обрабатываю ваш вопрос...")
        
        try:
            # Ищем релевантные чанки
            relevant_chunks = find_relevant_chunks(message.text)
            context = "\n\n".join(relevant_chunks) if relevant_chunks else ""
            
            # Генерируем ответ
            response = await generate_response(message.text, context)
            
            # Форматируем и отправляем ответ
            await processing_msg.edit_text(
                f"Вопрос: {message.text}\n\n"
                f"Ответ: {response}",
                reply_markup=main_kb
            )
        except Exception as e:
            logger.error(f"Ошибка при обработке вопроса: {e}")
            await processing_msg.edit_text(
                "😔 Извините, произошла ошибка при обработке вашего вопроса. Попробуйте позже.",
                reply_markup=main_kb
            )
    
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
            
            # Индексируем документ
            if await index_document(file_path):
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
        help_text = (
            '<b>Доступные команды:</b>\n\n'
            '/start - начать регистрацию\n'
            '/ask - задать вопрос ассистенту\n'
            'повтор - повторить попытку регистрации\n'
            '/help - помощь'
        )
        if message.from_user.id == ADMIN_CHAT_ID:
            help_text += '\n\n<b>Админ-команды:</b>\n' \
                        '/train - добавить документ для обучения\n' \
                        '/stats - статистика регистраций'
        
        await message.answer(help_text, parse_mode='HTML', reply_markup=main_kb)