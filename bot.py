import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
import requests
import json
import asyncio

# ==================== КОНФИГУРАЦИЯ ====================
API_TOKEN = '7987520742:AAHOXmsESsiP46HTQLPxu5PTzdDErj0XuwE'
GROQ_API_KEY = 'ВАШ_GROQ_API_KEY'
ADMIN_CHAT_ID = 925237471  # Замените на ваш реальный chat_id

# ==================== БАЗА ДАННЫХ ====================
AUTHORIZED_USERS = {}  # {user_id: {'name': 'ФИО', 'phone': 'телефон'}}
PENDING_REGISTRATIONS = {}  # {user_id: {'name': 'ФИО', 'phone': 'телефон', 'step': str}}
ROOMS = {
    '101': False,
    '102': False,
    '103': False
}

# ==================== НАСТРОЙКА ЛОГГИРОВАНИЯ ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ==================== ИНИЦИАЛИЗАЦИЯ ====================
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# ==================== КЛАВИАТУРЫ ====================
main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text='/status'), KeyboardButton(text='/memo')],
        [KeyboardButton(text='/help')]
    ],
    resize_keyboard=True
)

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================
def is_admin(user_id: int) -> bool:
    """Проверка, является ли пользователь администратором"""
    return user_id == ADMIN_CHAT_ID

async def send_guaranteed_message(chat_id: int, text: str, **kwargs):
    """Отправка сообщения с гарантированной доставкой"""
    for attempt in range(3):
        try:
            await bot.send_message(chat_id, text, **kwargs)
            return True
        except Exception as e:
            logger.error(f"Попытка {attempt + 1}: Ошибка отправки: {e}")
            await asyncio.sleep(1)
    return False

# ==================== ОБРАБОТЧИКИ КОМАНД ====================
@dp.message(Command('start'))
async def start_handler(message: types.Message):
    user_id = message.from_user.id
    if user_id in AUTHORIZED_USERS:
        await send_guaranteed_message(user_id, "Вы уже авторизованы!", reply_markup=main_kb)
    elif user_id in PENDING_REGISTRATIONS:
        await send_guaranteed_message(user_id, "Ваша заявка на рассмотрении...")
    else:
        PENDING_REGISTRATIONS[user_id] = {'step': 'name'}
        await send_guaranteed_message(user_id, "Добро пожаловать! Для регистрации введите ваше ФИО:")

@dp.message(lambda message: message.from_user.id in PENDING_REGISTRATIONS)
async def registration_handler(message: types.Message):
    user_id = message.from_user.id
    reg_data = PENDING_REGISTRATIONS[user_id]
    
    if reg_data['step'] == 'name':
        reg_data['name'] = message.text.strip()
        reg_data['step'] = 'phone'
        await send_guaranteed_message(user_id, "Отлично! Теперь введите ваш номер телефона:")
    
    elif reg_data['step'] == 'phone':
        reg_data['phone'] = message.text.strip()
        user_info = await bot.get_chat(user_id)
        notification = (
            f"<b>Новая заявка на регистрацию</b>\n\n"
            f"👤 <b>Пользователь:</b> {user_info.full_name}\n"
            f"🆔 <b>ID:</b> <code>{user_id}</code>\n"
            f"📝 <b>ФИО:</b> {reg_data['name']}\n"
            f"📞 <b>Телефон:</b> {reg_data['phone']}\n\n"
            f"Для подтверждения отправьте команду:\n"
            f"<code>/approve {user_id}</code>"
        )
        if await send_guaranteed_message(ADMIN_CHAT_ID, notification):
            await send_guaranteed_message(user_id, "✅ Ваша заявка отправлена администратору. Ожидайте подтверждения.")
        else:
            await send_guaranteed_message(user_id, "❌ Ошибка отправки заявки. Попробуйте позже.")
    # Удаление заявки переносим в approve_handler

@dp.message(Command('approve'))
async def approve_handler(message: types.Message):
    try:
        # Проверка прав администратора
        if not is_admin(message.from_user.id):
            await send_guaranteed_message(message.chat.id, "❌ Недостаточно прав!")
            return
        
        # Получение user_id из команды
        try:
            _, user_id = message.text.split()
            user_id = int(user_id)
        except:
            await send_guaranteed_message(message.chat.id, "❌ Формат: /approve user_id")
            return
        
        # Проверка существования заявки
        if user_id not in PENDING_REGISTRATIONS:
            await send_guaranteed_message(message.chat.id, "❌ Заявка не найдена!")
            return
            
        reg_data = PENDING_REGISTRATIONS[user_id]
        
        # Подтверждение регистрации
        AUTHORIZED_USERS[user_id] = {
            'name': reg_data['name'],
            'phone': reg_data['phone']
        }
        del PENDING_REGISTRATIONS[user_id]
        
        # Уведомление администратора
        await send_guaranteed_message(
            message.chat.id,
            f"✅ Пользователь {reg_data['name']} успешно зарегистрирован!"
        )
        
        # Уведомление пользователя
        await send_guaranteed_message(
            user_id,
            "🎉 Ваша регистрация подтверждена!\nТеперь вам доступны все функции бота.",
            reply_markup=main_kb
        )
        
    except Exception as e:
        logger.error(f"Ошибка в approve_handler: {e}")
        await send_guaranteed_message(message.chat.id, "⚠️ Произошла ошибка при обработке запроса")

@dp.message(Command('status'))
async def status_handler(message: types.Message):
    if message.from_user.id not in AUTHORIZED_USERS:
        await send_guaranteed_message(message.chat.id, "❌ Доступ запрещен!")
        return
    
    status = "\n".join(
        f"Номер {room}: {'✅ Убран' if cleaned else '❌ Не убран'}"
        for room, cleaned in ROOMS.items()
    )
    await send_guaranteed_message(
        message.chat.id,
        f"<b>🏨 Статус номеров:</b>\n\n{status}",
        parse_mode='HTML'
    )

@dp.message(Command('done'))
async def done_handler(message: types.Message):
    if message.from_user.id not in AUTHORIZED_USERS:
        await send_guaranteed_message(message.chat.id, "❌ Доступ запрещен!")
        return
    
    try:
        _, room = message.text.split()
        if room not in ROOMS:
            raise ValueError
        
        ROOMS[room] = True
        user = AUTHORIZED_USERS[message.from_user.id]
        
        await send_guaranteed_message(
            message.chat.id,
            f"✅ Номер {room} отмечен как убранный!"
        )
        
        await send_guaranteed_message(
            ADMIN_CHAT_ID,
            f"🧹 Номер {room} убран\n"
            f"👤 Уборщик: {user['name']}\n"
            f"📞 Контакт: {user['phone']}"
        )
    except:
        await send_guaranteed_message(
            message.chat.id,
            "❌ Используйте: /done номер_комнаты\nПример: /done 101"
        )

@dp.message(Command('memo'))
async def memo_handler(message: types.Message):
    if message.from_user.id not in AUTHORIZED_USERS:
        await send_guaranteed_message(message.chat.id, "❌ Доступ запрещен!")
        return
    await send_guaranteed_message(message.chat.id, "Напишите ваш вопрос по уборке:")

@dp.message(lambda message: message.reply_to_message and message.reply_to_message.text == "Напишите ваш вопрос по уборке:")
async def groq_handler(message: types.Message):
    if message.from_user.id not in AUTHORIZED_USERS:
        await send_guaranteed_message(message.chat.id, "❌ Доступ запрещен!")
        return
    
    await send_guaranteed_message(message.chat.id, "⏳ Ищу информацию...")
    
    try:
        url = 'https://api.groq.com/v1/chat/completions'
        headers = {
            'Authorization': f'Bearer {GROQ_API_KEY}',
            'Content-Type': 'application/json'
        }
        data = {
            'model': 'llama3-8b-8192',
            'messages': [
                {'role': 'system', 'content': 'Ты помощник по уборке номеров.'},
                {'role': 'user', 'content': message.text}
            ]
        }
        
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        answer = response.json()['choices'][0]['message']['content']
        
        await send_guaranteed_message(message.chat.id, answer)
    except Exception as e:
        logger.error(f"Ошибка Groq API: {e}")
        await send_guaranteed_message(message.chat.id, "⚠️ Не удалось получить ответ")

@dp.message(Command('help'))
async def help_handler(message: types.Message):
    help_text = (
        "<b>📋 Доступные команды:</b>\n\n"
        "/status - статус номеров\n"
        "/done [номер] - отметить номер как убранный\n"
        "/memo - задать вопрос по уборке\n"
        "/help - помощь"
    )
    await send_guaranteed_message(message.chat.id, help_text, parse_mode='HTML')

# ==================== ЗАПУСК БОТА ====================
async def main():
    logger.info("Бот запускается...")
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())