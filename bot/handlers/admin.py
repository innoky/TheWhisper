from aiogram import types, F, Dispatcher
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from db.wapi import ban_user, unban_user, add_pseudo_name, add_balance, set_balance, get_all_pseudo_names, deactivate_pseudo_name
import re
from aiogram.methods import EditMessageReplyMarkup
import aiohttp
import logging

def register_admin_handlers(dp: Dispatcher):
    @dp.callback_query(F.data.startswith("ban_"))
    async def handle_ban(callback: types.CallbackQuery):
        if not callback.data:
            await callback.answer("❌ Нет данных для бана")
            return
        user_id = int(callback.data.replace("ban_", ""))
        await ban_user(user_id=user_id)
        msg = callback.message
        if isinstance(msg, types.Message):
            await msg.edit_reply_markup(reply_markup=None)
        elif msg is not None and getattr(msg, "chat", None) is not None and getattr(msg, "message_id", None) is not None:
            await callback.bot(EditMessageReplyMarkup(chat_id=msg.chat.id, message_id=msg.message_id, reply_markup=None))
        await callback.answer("Пользователь забанен!", show_alert=True)
    
    @dp.message(Command("unban"))
    async def unban_handler(message: types.Message):
        if not message.text:
            await message.answer("Использование: /unban <user_id>")
            return
        parts = message.text.split()
        if len(parts) < 2:
            await message.answer("Использование: /unban <user_id>")
            return
        user_id = parts[1]
        if not user_id.isdigit():
            await message.answer("ID пользователя должен быть числом")
            return
        user_id = int(user_id)
        await unban_user(user_id=user_id)
        await message.answer(f"Пользователь {user_id} успешно разблокирован")

    @dp.message(Command("addpseudo"))
    async def addpseudo_handler(message: types.Message):
        if not message.text:
            await message.answer('Использование: /addpseudo "Никнейм" цена\nПример: /addpseudo "Ядерный шепот" 150')
            return
        pattern = r'^/addpseudo\s+"([^"]+)"\s+(\d+(?:\.\d+)?)'
        match = re.match(pattern, message.text)
        if not match:
            await message.answer('Использование: /addpseudo "Никнейм" цена\nПример: /addpseudo "Ядерный шепот" 150')
            return
        nickname = match.group(1)
        price = float(match.group(2))
        result = await add_pseudo_name(nickname, price)
        if 'id' in result:
            await message.answer(f'✅ Никнейм "{nickname}" успешно добавлен с ценой {price}!')
        elif 'pseudo' in result and 'unique' in str(result['pseudo']):
            await message.answer(f'❌ Никнейм "{nickname}" уже существует!')
        else:
            await message.answer(f'❌ Ошибка при добавлении никнейма: {result}')

    @dp.message(Command("addbalance"))
    async def addbalance_handler(message: types.Message):
        if not message.text:
            await message.answer('Использование: /addbalance user_id сумма')
            return
        parts = message.text.split()
        if len(parts) < 3:
            await message.answer('Использование: /addbalance user_id сумма')
            return
        user_id, amount = parts[1], parts[2]
        if not user_id.isdigit():
            await message.answer('user_id должен быть числом')
            return
        try:
            amount = float(amount)
        except ValueError:
            await message.answer('Сумма должна быть числом')
            return
        result = await add_balance(int(user_id), amount)
        if 'balance' in result:
            await message.answer(f'✅ Баланс пользователя {user_id} увеличен. Новый баланс: {result["balance"]}')
        else:
            await message.answer(f'❌ Ошибка: {result}')

    @dp.message(Command("setbalance"))
    async def setbalance_handler(message: types.Message):
        if not message.text:
            await message.answer('Использование: /setbalance user_id сумма')
            return
        parts = message.text.split()
        if len(parts) < 3:
            await message.answer('Использование: /setbalance user_id сумма')
            return
        user_id, amount = parts[1], parts[2]
        if not user_id.isdigit():
            await message.answer('user_id должен быть числом')
            return
        try:
            amount = float(amount)
        except ValueError:
            await message.answer('Сумма должна быть числом')
            return
        result = await set_balance(int(user_id), amount)
        if 'balance' in result:
            await message.answer(f'✅ Баланс пользователя {user_id} установлен на {result["balance"]}')
        else:
            await message.answer(f'❌ Ошибка: {result}')

    @dp.message(Command("allpseudos"))
    async def allpseudos_handler(message: types.Message):
        pseudos = await get_all_pseudo_names()
        if isinstance(pseudos, dict) and pseudos.get("error"):
            await message.answer(f'❌ Ошибка: {pseudos}')
            return
        if not pseudos:
            await message.answer('Нет никнеймов в системе.')
            return
        lines = [
            f"ID: {p['id']} | '{p['pseudo']}' | Цена: {p['price']} | {'✅' if p['is_available'] else '❌'}"
            for p in pseudos
        ]
        text = '\n'.join(lines)
        await message.answer(f'<b>Все никнеймы:</b>\n{text}', parse_mode='HTML')

    @dp.message(Command("deactivate"))
    async def deactivate_handler(message: types.Message):
        if not message.text:
            await message.answer('Использование: /deactivate pseudo_id')
            return
        parts = message.text.split()
        if len(parts) < 2 or not parts[1].isdigit():
            await message.answer('Использование: /deactivate pseudo_id')
            return
        pseudo_id = int(parts[1])
        result = await deactivate_pseudo_name(pseudo_id)
        if 'status' in result and result['status'] == 'deactivated':
            await message.answer(f'✅ Никнейм {pseudo_id} деактивирован!')
        else:
            await message.answer(f'❌ Ошибка: {result}')