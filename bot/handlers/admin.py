from aiogram import types, F, Dispatcher
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from db.wapi import ban_user, unban_user

def register_admin_handlers(dp: Dispatcher):
    @dp.callback_query(F.data.startswith("ban_"))
    async def handle_ban(callback: types.CallbackQuery):
        print("test")
        if not callback.data:
            await callback.answer("❌ Нет данных для бана")
            return
        user_id = callback.data.replace("ban_", "")
        user_id = int(user_id)
        print("TESTTSTST")
        await ban_user(user_id=user_id)
        await callback.message.delete_reply_markup()
    
    @dp.message(Command("unban"))
    async def unban_handler(message: types.Message):
        try:
            # Разбиваем сообщение на части
            parts = message.text.split()
            
            # Проверяем, что указан user_id (команда + аргумент)
            if len(parts) < 2:
                await message.answer("Использование: /unban <user_id>")
                return
                
            user_id = parts[1]
            
            # Проверяем, что user_id состоит только из цифр
            if not user_id.isdigit():
                await message.answer("ID пользователя должен быть числом")
                return
                
            # Преобразуем в int и вызываем функцию разбана
            user_id = int(user_id)
            await unban_user(user_id=user_id)
            await message.answer(f"Пользователь {user_id} успешно разблокирован")
            
        except IndexError:
            await message.answer("Использование: /unban <user_id>")
        except Exception as e:
            print(f"Ошибка при разблокировке: {e}")
            await message.answer("Произошла ошибка при разблокировке")