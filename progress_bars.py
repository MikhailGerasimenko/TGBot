#!/usr/bin/env python3
"""
Модуль для работы с прогресс-барами в Telegram
"""

import asyncio
import time
from typing import Optional, Callable
from aiogram import Bot
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

class ProgressBar:
    """Класс для создания и обновления прогресс-баров"""
    
    def __init__(self, bot: Bot, chat_id: int, message_id: Optional[int] = None):
        self.bot = bot
        self.chat_id = chat_id
        self.message_id = message_id
        self.start_time = time.time()
        self.is_active = False
        
    async def start(self, text: str = "🤖 Генерирую ответ...") -> int:
        """Запускает прогресс-бар"""
        self.is_active = True
        self.start_time = time.time()
        
        # Создаем начальный прогресс-бар
        progress_text = self._create_progress_text(text, 0)
        
        message = await self.bot.send_message(
            chat_id=self.chat_id,
            text=progress_text,
            parse_mode="HTML"
        )
        
        self.message_id = message.message_id
        return self.message_id
    
    async def update(self, progress: float, text: str = None) -> bool:
        """Обновляет прогресс-бар"""
        if not self.is_active or not self.message_id:
            return False
            
        try:
            progress_text = self._create_progress_text(text or "🤖 Генерирую ответ...", progress)
            
            await self.bot.edit_message_text(
                chat_id=self.chat_id,
                message_id=self.message_id,
                text=progress_text,
                parse_mode="HTML"
            )
            return True
        except Exception as e:
            print(f"Ошибка обновления прогресс-бара: {e}")
            return False
    
    async def complete(self, final_text: str = "✅ Готово!") -> bool:
        """Завершает прогресс-бар"""
        if not self.is_active or not self.message_id:
            return False
            
        try:
            elapsed_time = time.time() - self.start_time
            
            # Создаем финальное сообщение
            final_message = f"""
{final_text}

⏱️ Время генерации: {elapsed_time:.1f} сек
🎯 Статус: Завершено
            """.strip()
            
            await self.bot.edit_message_text(
                chat_id=self.chat_id,
                message_id=self.message_id,
                text=final_message,
                parse_mode="HTML"
            )
            
            self.is_active = False
            return True
        except Exception as e:
            print(f"Ошибка завершения прогресс-бара: {e}")
            return False
    
    async def error(self, error_text: str = "❌ Ошибка генерации") -> bool:
        """Показывает ошибку в прогресс-баре"""
        if not self.is_active or not self.message_id:
            return False
            
        try:
            elapsed_time = time.time() - self.start_time
            
            error_message = f"""
{error_text}

⏱️ Время: {elapsed_time:.1f} сек
🎯 Статус: Ошибка
            """.strip()
            
            await self.bot.edit_message_text(
                chat_id=self.chat_id,
                message_id=self.message_id,
                text=error_message,
                parse_mode="HTML"
            )
            
            self.is_active = False
            return True
        except Exception as e:
            print(f"Ошибка показа ошибки: {e}")
            return False
    
    def _create_progress_text(self, text: str, progress: float) -> str:
        """Создает текст прогресс-бара"""
        # Ограничиваем прогресс от 0 до 1
        progress = max(0, min(1, progress))
        
        # Создаем визуальный прогресс-бар
        bar_length = 20
        filled_length = int(bar_length * progress)
        bar = "█" * filled_length + "░" * (bar_length - filled_length)
        
        # Процент выполнения
        percentage = int(progress * 100)
        
        # Эмодзи в зависимости от прогресса
        if progress < 0.3:
            emoji_icon = "🤔"
        elif progress < 0.7:
            emoji_icon = "💭"
        elif progress < 1.0:
            emoji_icon = "✨"
        else:
            emoji_icon = "✅"
        
        # Время с начала
        elapsed_time = time.time() - self.start_time
        
        progress_text = f"""
{emoji_icon} <b>{text}</b>

<code>{bar}</code> {percentage}%

⏱️ Время: {elapsed_time:.1f} сек
🎯 Статус: Генерация...
        """.strip()
        
        return progress_text

class ProgressManager:
    """Менеджер для управления прогресс-барами"""
    
    def __init__(self, bot: Bot):
        self.bot = bot
        self.active_bars = {}
    
    async def start_progress(self, chat_id: int, text: str = "🤖 Генерирую ответ...") -> int:
        """Запускает новый прогресс-бар"""
        # Останавливаем предыдущий, если есть
        await self.stop_progress(chat_id)
        
        # Создаем новый
        progress_bar = ProgressBar(self.bot, chat_id)
        message_id = await progress_bar.start(text)
        
        self.active_bars[chat_id] = progress_bar
        return message_id
    
    async def update_progress(self, chat_id: int, progress: float, text: str = None) -> bool:
        """Обновляет прогресс-бар"""
        if chat_id not in self.active_bars:
            return False
        
        return await self.active_bars[chat_id].update(progress, text)
    
    async def complete_progress(self, chat_id: int, final_text: str = "✅ Готово!") -> bool:
        """Завершает прогресс-бар"""
        if chat_id not in self.active_bars:
            return False
        
        success = await self.active_bars[chat_id].complete(final_text)
        if success:
            del self.active_bars[chat_id]
        return success
    
    async def error_progress(self, chat_id: int, error_text: str = "❌ Ошибка генерации") -> bool:
        """Показывает ошибку в прогресс-баре"""
        if chat_id not in self.active_bars:
            return False
        
        success = await self.active_bars[chat_id].error(error_text)
        if success:
            del self.active_bars[chat_id]
        return success
    
    async def stop_progress(self, chat_id: int) -> bool:
        """Останавливает прогресс-бар"""
        if chat_id not in self.active_bars:
            return False
        
        try:
            await self.active_bars[chat_id].complete("⏹️ Остановлено")
            del self.active_bars[chat_id]
            return True
        except:
            return False

# Функция для асинхронного обновления прогресса
async def update_progress_async(progress_manager: ProgressManager, chat_id: int, 
                              duration: float = 10.0, steps: int = 20):
    """Асинхронно обновляет прогресс-бар"""
    step_duration = duration / steps
    
    for i in range(steps + 1):
        if chat_id not in progress_manager.active_bars:
            break
            
        progress = i / steps
        
        # Разные тексты на разных этапах
        if progress < 0.3:
            text = "🤔 Анализирую вопрос..."
        elif progress < 0.6:
            text = "💭 Ищу информацию..."
        elif progress < 0.9:
            text = "✨ Формирую ответ..."
        else:
            text = "✅ Завершаю..."
        
        await progress_manager.update_progress(chat_id, progress, text)
        await asyncio.sleep(step_duration) 