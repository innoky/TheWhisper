from aiogram import types, F, Dispatcher
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from db.wapi import ban_user, unban_user, add_pseudo_name, add_balance, set_balance, get_all_pseudo_names, deactivate_pseudo_name, set_user_level, get_user_info, get_active_posts_count, get_recent_posts, get_all_users, get_queue_info, recalculate_queue_after_immediate_publication, get_user_pseudo_names_full
import re
from aiogram.methods import EditMessageReplyMarkup
import aiohttp
import logging
from datetime import datetime, timezone, timedelta
import os
import difflib
from aiogram.utils.formatting import ExpandableBlockQuote, Bold, Text, Italic, TextLink, Underline, Code, Pre, BlockQuote

# Импортируем константы из suggest
POST_INTERVAL_MINUTES = 30

async def is_admin(user_id: int) -> bool:
    """
    Проверяет, является ли пользователь администратором.
    
    Args:
        user_id: ID пользователя для проверки
        
    Returns:
        bool: True если пользователь является администратором, False в противном случае
    """
    try:
        logging.info(f"[is_admin] Checking admin status for user {user_id}")
        user_info = await get_user_info(user_id)
        logging.info(f"[is_admin] User info for {user_id}: {user_info}")
        
        if 'error' in user_info:
            logging.warning(f"[is_admin] Error getting user info for {user_id}: {user_info['error']}")
            return False
        
        is_admin_status = user_info.get('is_admin', False)
        logging.info(f"[is_admin] User {user_id} admin status: {is_admin_status}")
        return bool(is_admin_status)
    except Exception as e:
        logging.error(f"[is_admin] Exception checking admin status for {user_id}: {e}")
        return False

def register_admin_handlers(dp: Dispatcher):
    @dp.callback_query(F.data.startswith("ban_"))
    async def handle_ban(callback: types.CallbackQuery):
        if not callback.data:
            await callback.answer("❌ Нет данных для бана")
            return
        user_id = int(callback.data.replace("ban_", ""))
        
        # Получаем информацию о пользователе
        user_info = await get_user_info(user_id)
        username = "Неизвестно"
        if 'error' not in user_info:
            username = user_info.get('username', 'N/A') or user_info.get('firstname', 'N/A')
        
        # Выполняем бан
        result = await ban_user(user_id=user_id)
        
        msg = callback.message
        if isinstance(msg, types.Message):
            await msg.edit_reply_markup(reply_markup=None)
        elif msg is not None and getattr(msg, "chat", None) is not None and getattr(msg, "message_id", None) is not None:
            chat_id = msg.chat.id if getattr(msg, 'chat', None) is not None else None
            message_id = msg.message_id if getattr(msg, 'message_id', None) is not None else None
            if chat_id is not None and message_id is not None:
                await callback.bot(EditMessageReplyMarkup(chat_id=chat_id, message_id=message_id, reply_markup=None))
        
        # Формируем информативное сообщение
        if 'error' in result:
            ban_message = f"❌ <b>Ошибка при бане пользователя!</b>\n\n"
            ban_message += f"👤 <b>Пользователь:</b> {username} (ID: {user_id})\n"
            ban_message += f"🚫 <b>Ошибка:</b> {result['error']}"
        else:
            ban_message = f"🚫 <b>Пользователь забанен!</b>\n\n"
            ban_message += f"👤 <b>Пользователь:</b> {username} (ID: {user_id})\n"
            ban_message += f"⏰ <b>Время:</b> {datetime.now(timezone(timedelta(hours=3))).strftime('%d.%m.%Y в %H:%M')}\n"
            admin_name = callback.from_user.username if callback.from_user and getattr(callback.from_user, 'username', None) else None
            if not admin_name:
                admin_name = callback.from_user.first_name if callback.from_user and getattr(callback.from_user, 'first_name', None) else "Админ"
            ban_message += f"👮 <b>Админ:</b> {admin_name}"
        
        await callback.answer("Пользователь забанен!", show_alert=True)
    
    @dp.message(Command("unban"))
    async def unban_handler(message: types.Message):
        if not message.text:
            await message.answer("Использование: /unban &lt;user_id&gt;")
            return
        parts = message.text.split()
        if len(parts) < 2:
            await message.answer("Использование: /unban &lt;user_id&gt;")
            return
        user_id = parts[1]
        if not user_id.isdigit():
            await message.answer("ID пользователя должен быть числом")
            return
        user_id = int(user_id)
        
        # Получаем информацию о пользователе
        user_info = await get_user_info(user_id)
        username = "Неизвестно"
        if 'error' not in user_info:
            username = user_info.get('username', 'N/A') or user_info.get('firstname', 'N/A')
        
        # Выполняем разбан
        result = await unban_user(user_id=user_id)
        
        # Формируем информативное сообщение
        if 'error' in result:
            unban_message = f"❌ <b>Ошибка при разбане пользователя!</b>\n\n"
            unban_message += f"👤 <b>Пользователь:</b> {username} (ID: {user_id})\n"
            unban_message += f"🚫 <b>Ошибка:</b> {result['error']}"
        else:
            unban_message = f"✅ <b>Пользователь разблокирован!</b>\n\n"
            unban_message += f"👤 <b>Пользователь:</b> {username} (ID: {user_id})\n"
            unban_message += f"⏰ <b>Время:</b> {datetime.now(timezone(timedelta(hours=3))).strftime('%d.%m.%Y в %H:%M')}\n"
            admin_name = message.from_user.username if message.from_user and getattr(message.from_user, 'username', None) else None
            if not admin_name:
                admin_name = message.from_user.first_name if message.from_user and getattr(message.from_user, 'first_name', None) else "Админ"
            unban_message += f"👮 <b>Админ:</b> {admin_name}"
        
        await message.answer(unban_message, parse_mode="HTML")

    @dp.message(Command("levelup"))
    async def levelup_handler(message: types.Message):
        """Повышает уровень пользователя"""
        if not message.text:
            await message.answer("Использование: /levelup &lt;user_id&gt;")
            return
        parts = message.text.split()
        if len(parts) < 2:
            await message.answer("Использование: /levelup &lt;user_id&gt;")
            return
        user_id = parts[1]
        if not user_id.isdigit():
            await message.answer("ID пользователя должен быть числом")
            return
        user_id = int(user_id)
        
        # Получаем текущий уровень пользователя
        user_info = await get_user_info(user_id)
        if 'error' in user_info:
            error_text = user_info.get('error', '')
            if '404' in error_text:
                await message.answer(f'<b>Пользователь с ID {user_id} не существует.</b>', parse_mode='HTML')
            else:
                await message.answer(f'<b>Ошибка получения информации о пользователе:</b> {error_text}', parse_mode='HTML')
            return
        
        current_level = int(user_info.get('level', 1))
        new_level = min(current_level + 1, 10)  # Не больше 10
        
        if new_level == current_level:
            await message.answer(f"❌ Пользователь {user_id} уже имеет максимальный уровень (10)")
            return
        
        # Устанавливаем новый уровень
        result = await set_user_level(user_id, new_level)
        if 'error' in result:
            await message.answer(f"❌ Ошибка при повышении уровня: {result['error']}", parse_mode='HTML')
            return
        
        await message.answer(f"<b>Уровень пользователя {user_id} повышен с {current_level} до {new_level}</b>", parse_mode='HTML')
        
        # Отправляем уведомление пользователю
        try:
            if message.bot:
                await message.bot.send_message(
                    chat_id=user_id,
                    text=f"<b>Ваш уровень повышен!</b>\n\n"
                         f"Старый уровень: {current_level}\n"
                         f"Новый уровень: {new_level}\n\n"
                         f"Теперь за каждый пост вы получаете больше токенов",
                    parse_mode="HTML"
                )
        except Exception as e:
            logging.warning(f"Could not send levelup notification to user {user_id}: {e}")

    @dp.message(Command("leveldown"))
    async def leveldown_handler(message: types.Message):
        """Понижает уровень пользователя"""
        if not message.text:
            await message.answer("Использование: /leveldown &lt;user_id&gt;")
            return
        parts = message.text.split()
        if len(parts) < 2:
            await message.answer("Использование: /leveldown &lt;user_id&gt;")
            return
        user_id = parts[1]
        if not user_id.isdigit():
            await message.answer("ID пользователя должен быть числом")
            return
        user_id = int(user_id)
        
        # Получаем текущий уровень пользователя
        user_info = await get_user_info(user_id)
        if 'error' in user_info:
            error_text = user_info.get('error', '')
            if '404' in error_text:
                await message.answer(f'<b>Пользователь с ID {user_id} не существует.</b>', parse_mode='HTML')
            else:
                await message.answer(f'<b>Ошибка получения информации о пользователе:</b> {error_text}', parse_mode='HTML')
            return
        
        current_level = int(user_info.get('level', 1))
        new_level = max(current_level - 1, 1)  # Не меньше 1
        
        if new_level == current_level:
            await message.answer(f"❌ Пользователь {user_id} уже имеет минимальный уровень (1)")
            return
        
        # Устанавливаем новый уровень
        result = await set_user_level(user_id, new_level)
        if 'error' in result:
            await message.answer(f"❌ Ошибка при понижении уровня: {result['error']}", parse_mode='HTML')
            return
        
        await message.answer(f"<b>Уровень пользователя {user_id} понижен с {current_level} до {new_level}</b>", parse_mode='HTML')
        
        # Отправляем уведомление пользователю
        try:
            if message.bot:
                await message.bot.send_message(
                    chat_id=user_id,
                    text=f"<b>Ваш уровень понижен!</b>\n\n"
                         f"Старый уровень: {current_level}\n"
                         f"Новый уровень: {new_level}\n\n"
                         f"Теперь за каждый пост вы получаете меньше токенов",
                    parse_mode="HTML"
                )
        except Exception as e:
            logging.warning(f"Could not send leveldown notification to user {user_id}: {e}")

    @dp.message(Command("addpseudo"))
    async def addpseudo_handler(message: types.Message):
        if not message.text:
            await message.answer('Использование: /addpseudo "Никнейм" цена\nПример: /addpseudo "Ядерный шепот" 150', parse_mode='HTML')
            return
        pattern = r'^/addpseudo\s+"([^"]+)"\s+(\d+(?:\.\d+)?)'
        match = re.match(pattern, message.text)
        if not match:
            await message.answer('Использование: /addpseudo "Никнейм" цена\nПример: /addpseudo "Ядерный шепот" 150', parse_mode='HTML')
            return
        nickname = match.group(1)
        price = float(match.group(2))
        
        result = await add_pseudo_name(nickname, price)
        
        if 'id' in result:
            pseudo_message = f"<b>Псевдоним успешно добавлен</b>\n\n"
            pseudo_message += f"<b>Имя:</b> \"{nickname}\"\n"
            pseudo_message += f"<b>Цена:</b> {price:.2f} т.\n"
            pseudo_message += f"<b>ID:</b> {result['id']}\n"
            pseudo_message += f"<b>Статус:</b> Доступен для покупки\n"
            pseudo_message += f"<b>Время:</b> {datetime.now(timezone(timedelta(hours=3))).strftime('%d.%m.%Y в %H:%M')}\n"
            admin_name = message.from_user.username if message.from_user and getattr(message.from_user, 'username', None) else None
            if not admin_name:
                admin_name = message.from_user.first_name if message.from_user and getattr(message.from_user, 'first_name', None) else "Админ"
            pseudo_message += f"👮 <b>Админ:</b> {admin_name}"
        elif 'pseudo' in result and 'unique' in str(result['pseudo']):
            pseudo_message = f"<b>Псевдоним уже существует</b>\n\n"
            pseudo_message += f"<b>Имя:</b> \"{nickname}\"\n"
            pseudo_message += f"<b>Ошибка:</b> Псевдоним с таким именем уже существует\n"
            pseudo_message += f"<b>Совет:</b> Используйте другое имя или проверьте существующие псевдонимы командой /allpseudos"
        else:
            pseudo_message = f"<b>Ошибка при добавлении псевдонима</b>\n\n"
            pseudo_message += f"<b>Имя:</b> \"{nickname}\"\n"
            pseudo_message += f"<b>Цена:</b> {price:.2f} т.\n"
            pseudo_message += f"<b>Ошибка:</b> {result}"
        
        await message.answer(pseudo_message, parse_mode="HTML")

    @dp.message(Command("addbalance"))
    async def addbalance_handler(message: types.Message):
        if not message.text:
            await message.answer('Использование: /addbalance user_id сумма', parse_mode='HTML')
            return
        parts = message.text.split()
        if len(parts) < 3:
            await message.answer('Использование: /addbalance user_id сумма', parse_mode='HTML')
            return
        user_id, amount = parts[1], parts[2]
        if not user_id.isdigit():
            await message.answer('user_id должен быть числом', parse_mode='HTML')
            return
        try:
            amount = float(amount)
        except ValueError:
            await message.answer('Сумма должна быть числом', parse_mode='HTML')
            return
        
        user_id = int(user_id)
        
        # Получаем информацию о пользователе и текущий баланс
        user_info = await get_user_info(user_id)
        if 'error' in user_info:
            error_text = user_info.get('error', '')
            if '404' in error_text:
                await message.answer(f'<b>Пользователь с ID {user_id} не существует.</b>', parse_mode='HTML')
            else:
                await message.answer(f'<b>Ошибка получения информации о пользователе:</b> {error_text}', parse_mode='HTML')
            return
        
        username = user_info.get('username', 'N/A') or user_info.get('firstname', 'N/A')
        old_balance = float(user_info.get('balance', 0))
        
        # Выполняем операцию
        result = await add_balance(user_id, amount)
        
        if 'balance' in result:
            new_balance = float(result["balance"])
            balance_message = f"<b>Баланс пользователя обновлен</b>\n\n"
            balance_message += f"<b>Пользователь:</b> {username} (ID: {user_id})\n"
            balance_message += f"<b>Старый баланс:</b> {old_balance} т.\n"
            balance_message += f"<b>Добавлено:</b> +{amount} т.\n"
            balance_message += f"<b>Новый баланс:</b> {result['balance']} т.\n"
            balance_message += f"<b>Время:</b> {datetime.now(timezone(timedelta(hours=3))).strftime('%d.%m.%Y в %H:%M')}\n"
            admin_name = message.from_user.username if message.from_user and getattr(message.from_user, 'username', None) else None
            if not admin_name:
                admin_name = message.from_user.first_name if message.from_user and getattr(message.from_user, 'first_name', None) else "Админ"
            balance_message += f"👮 <b>Админ:</b> {admin_name}"
        else:
            balance_message = f"<b>Ошибка обновления баланса</b>\n\n"
            balance_message += f"<b>Пользователь:</b> {username} (ID: {user_id})\n"
            balance_message += f"<b>Сумма:</b> {amount} т.\n"
            balance_message += f"<b>Ошибка:</b> {result}"
        
        await message.answer(balance_message, parse_mode="HTML")

    @dp.message(Command("setbalance"))
    async def setbalance_handler(message: types.Message):
        if not message.text:
            await message.answer('Использование: /setbalance user_id сумма', parse_mode='HTML')
            return
        parts = message.text.split()
        if len(parts) < 3:
            await message.answer('Использование: /setbalance user_id сумма', parse_mode='HTML')
            return
        user_id, amount = parts[1], parts[2]
        if not user_id.isdigit():
            await message.answer('user_id должен быть числом', parse_mode='HTML')
            return
        try:
            amount = float(amount)
        except ValueError:
            await message.answer('Сумма должна быть числом', parse_mode='HTML')
            return
        
        user_id = int(user_id)
        
        # Получаем информацию о пользователе и текущий баланс
        user_info = await get_user_info(user_id)
        if 'error' in user_info:
            error_text = user_info.get('error', '')
            if '404' in error_text:
                await message.answer(f'<b>Пользователь с ID {user_id} не существует.</b>', parse_mode='HTML')
            else:
                await message.answer(f'<b>Ошибка получения информации о пользователе:</b> {error_text}', parse_mode='HTML')
            return
        
        username = user_info.get('username', 'N/A') or user_info.get('firstname', 'N/A')
        old_balance = float(user_info.get('balance', 0))
        
        # Выполняем операцию
        result = await set_balance(user_id, amount)
        
        if 'balance' in result:
            balance_message = f"<b>Баланс пользователя установлен</b>\n\n"
            balance_message += f"<b>Пользователь:</b> {username} (ID: {user_id})\n"
            balance_message += f"<b>Старый баланс:</b> {old_balance} т.\n"
            balance_message += f"<b>Новый баланс:</b> {result['balance']} т.\n"
            balance_message += f"<b>Время:</b> {datetime.now(timezone(timedelta(hours=3))).strftime('%d.%m.%Y в %H:%M')}\n"
            admin_name = message.from_user.username if message.from_user and getattr(message.from_user, 'username', None) else None
            if not admin_name:
                admin_name = message.from_user.first_name if message.from_user and getattr(message.from_user, 'first_name', None) else "Админ"
            balance_message += f"👮 <b>Админ:</b> {admin_name}"
        else:
            balance_message = f"<b>Ошибка установки баланса</b>\n\n"
            balance_message += f"<b>Пользователь:</b> {username} (ID: {user_id})\n"
            balance_message += f"<b>Сумма:</b> {amount} т.\n"
            balance_message += f"<b>Ошибка:</b> {result}"
        
        await message.answer(balance_message, parse_mode="HTML")

    @dp.message(Command("allpseudos"))
    async def allpseudos_handler(message: types.Message):
        pseudos = await get_all_pseudo_names()
        if isinstance(pseudos, dict) and pseudos.get("error"):
            await message.answer(f'<b>Ошибка:</b> {pseudos}', parse_mode='HTML')
            return
        if not pseudos:
            await message.answer('<b>Нет псевдонимов в системе</b>', parse_mode='HTML')
            return
        
        # Подсчитываем статистику
        total_count = len(pseudos)
        available_count = sum(1 for p in pseudos if p.get('is_available', False))
        unavailable_count = total_count - available_count
        
        # Формируем заголовок с статистикой
        header = f"<b>Все псевдонимы ({total_count})</b>\n\n"
        header += f"<b>Статистика:</b>\n"
        header += f"Доступно: {available_count}\n"
        header += f"Недоступно: {unavailable_count}\n\n"
        header += f"<b>Список:</b>\n"
        
        # Формируем список псевдонимов
        lines = []
        for p in pseudos:
            status_icon = "✅" if p.get('is_available', False) else "❌"
            status_text = "Доступен" if p.get('is_available', False) else "Недоступен"
            lines.append(f"{status_icon} <b>ID {p['id']}:</b> \"{p['pseudo']}\" | {p['price']} т. | {status_text}")
        
        text = header + '\n'.join(lines)
        
        # Разбиваем на части, если сообщение слишком длинное
        if len(text) > 4096:
            parts = []
            current_part = ""
            for line in lines:
                if len(current_part + line + '\n') > 4000:
                    parts.append(header + current_part)
                    current_part = line + '\n'
                else:
                    current_part += line + '\n'
            if current_part:
                parts.append(header + current_part)
            
            for i, part in enumerate(parts, 1):
                await message.answer(f"{part}\n\n📄 <b>Страница {i} из {len(parts)}</b>", parse_mode='HTML')
        else:
            await message.answer(text, parse_mode='HTML')

    @dp.message(Command("deactivate"))
    async def deactivate_handler(message: types.Message):
        if not message.text:
            await message.answer('Использование: /deactivate pseudo_id', parse_mode='HTML')
            return
        parts = message.text.split()
        if len(parts) < 2 or not parts[1].isdigit():
            await message.answer('Использование: /deactivate pseudo_id', parse_mode='HTML')
            return
        pseudo_id = int(parts[1])
        
        # Получаем информацию о псевдониме
        pseudos = await get_all_pseudo_names()
        pseudo_name = "Неизвестно"
        if isinstance(pseudos, list):
            for pseudo in pseudos:
                if pseudo.get('id') == pseudo_id:
                    pseudo_name = pseudo.get('pseudo', 'Неизвестно')
                    break
        
        result = await deactivate_pseudo_name(pseudo_id)
        
        if 'success' in result:
            deactivate_message = f"<b>Псевдоним деактивирован</b>\n\n"
            deactivate_message += f"<b>Имя:</b> \"{pseudo_name}\"\n"
            deactivate_message += f"<b>ID:</b> {pseudo_id}\n"
            deactivate_message += f"<b>Статус:</b> Недоступен для покупки\n"
            deactivate_message += f"<b>Время:</b> {datetime.now(timezone(timedelta(hours=3))).strftime('%d.%m.%Y в %H:%M')}\n"
            admin_name = message.from_user.username if message.from_user and getattr(message.from_user, 'username', None) else None
            if not admin_name:
                admin_name = message.from_user.first_name if message.from_user and getattr(message.from_user, 'first_name', None) else "Админ"
            deactivate_message += f"👮 <b>Админ:</b> {admin_name}"
        else:
            deactivate_message = f"<b>Ошибка деактивации псевдонима</b>\n\n"
            deactivate_message += f"<b>Имя:</b> \"{pseudo_name}\"\n"
            deactivate_message += f"<b>ID:</b> {pseudo_id}\n"
            deactivate_message += f"<b>Ошибка:</b> {result}"
        
        await message.answer(deactivate_message, parse_mode="HTML")

    @dp.message(Command("stats"))
    async def stats_handler(message: types.Message):
        from datetime import datetime, timezone
        import aiohttp
        user_id = message.from_user.id
        user_info = await get_user_info(user_id)
        if not user_info or user_info.get('error'):
            await message.answer("<b>Ошибка: не удалось получить информацию о пользователе</b>", parse_mode="HTML")
            return
        pseudos = await get_user_pseudo_names_full(user_id)
        pseudos_str = ', '.join([p[1] for p in pseudos]) if pseudos else 'Нет'
        API_BASE = 'http://backend:8000/api/'
        posts = []
        async with aiohttp.ClientSession() as session:
            url = f"{API_BASE}posts/?author={user_id}&page_size=1000"
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if isinstance(data, dict) and 'results' in data:
                        posts = data['results']
                    elif isinstance(data, list):
                        posts = data
        total = len(posts)
        posted = sum(1 for p in posts if p.get('is_posted'))
        rejected = sum(1 for p in posts if p.get('is_rejected'))
        queued = sum(1 for p in posts if not p.get('is_posted') and not p.get('is_rejected'))
        reg_date = user_info.get('created_at')
        reg_dt = None
        days_with_us = None
        reg_str = 'N/A'
        if reg_date:
            try:
                reg_dt = datetime.fromisoformat(reg_date)
                reg_str = reg_dt.strftime('%d.%m.%Y, %H:%M')
                now = datetime.now(timezone.utc)
                days_with_us = (now - reg_dt.replace(tzinfo=timezone.utc)).days
            except Exception:
                reg_str = reg_date
        # Первый пост
        first_post = min(posts, key=lambda p: p.get('created_at', '9999'), default=None)
        first_post_str = ''
        if first_post and first_post.get('created_at'):
            try:
                first_dt = datetime.fromisoformat(first_post['created_at'])
                first_post_str = f"Ваша первая работа создана {first_dt.strftime('%d.%m.%Y, %H:%M')}\n"
            except Exception:
                first_post_str = f"Ваша первая работа создана {first_post['created_at']}\n"
            first_post_str += f"<i>{first_post.get('content','')[:120]}{'...' if len(first_post.get('content',''))>120 else ''}</i>\n"
        # Топ-3 самых длинных поста
        top_posts = sorted(posts, key=lambda p: len(p.get('content','')), reverse=True)[:3]
        top_posts_str = ''
        if top_posts and total > 0:
            top_posts_str = '<b>🏆 Топ-3 самых длинных поста:</b>\n'
            for i, p in enumerate(top_posts, 1):
                frag = p.get('content','')[:60].replace('\n',' ')
                top_posts_str += f"{i}. {frag}{'...' if len(p.get('content',''))>60 else ''} ({len(p.get('content',''))} симв.)\n"
        # Формируем красивый вывод
        stats_message = f"<b>Статистика {user_info.get('firstname','') or ''} {user_info.get('lastname','') or ''}</b>\n"
        stats_message += f"@{user_info.get('username','N/A')}\n"
        stats_message += f"\n"
        if reg_dt and days_with_us is not None:
            stats_message += f"⏱️ Вы с нами с {reg_str}, уже <b>{days_with_us}</b> дней.\n"
        stats_message += f"\n"
        stats_message += f"За это время вы успели сделать <b>{total}</b> постов!\n"
        stats_message += f"<b>✅ Опубликовано:</b> {posted}\n"
        stats_message += f"<b>❌ Отклонено:</b> {rejected}\n"
        stats_message += f"<b>🕓 В очереди:</b> {queued}\n"
        stats_message += f"\n"
        stats_message += f"<b>🦄 Ваши псевдонимы:</b> {pseudos_str}\n"
        stats_message += f"<b>💰 Баланс:</b> {user_info.get('balance','N/A')} т.\n"
        stats_message += f"<b>🏅 Уровень:</b> {user_info.get('level','N/A')}\n"
        stats_message += f"\n"
        if top_posts_str:
            stats_message += top_posts_str + '\n'
        if first_post_str:
            stats_message += f"<b>Первая работа</b>\n{first_post_str}\n"
        stats_message += f"<i>Спасибо за активность! Продолжай щитпостить и зарабатывать токены!</i>"
        await message.answer(stats_message, parse_mode="HTML")

    @dp.message(Command("getuser"))
    async def getuser_handler(message: types.Message):
        if not message.text:
            await message.answer("Использование: /getuser <username или ID>")
            return
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            await message.answer("Использование: /getuser <username или ID>")
            return
        query = parts[1].strip().lstrip('@')
        if not query:
            await message.answer("Введите ник, часть ника или ID пользователя")
            return
        
        # Сначала проверяем, не является ли запрос числовым ID
        if query.isdigit():
            user_id = int(query)
            user_info = await get_user_info(user_id)
            if 'error' not in user_info:
                user = user_info
                reply = "<b>Пользователь найден по ID:</b>\n\n"
                reply += (
                    f"ID: <code>{user['id']}</code>\n"
                    f"Username: @{format_username(user.get('username'))}\n"
                    f"Имя: {user.get('firstname', '')} {user.get('lastname', '')}\n"
                    f"Баланс: {user.get('balance', 'N/A')}\n"
                    f"Уровень: {user.get('level', 'N/A')}\n"
                    f"Админ: {'Да' if user.get('is_admin') else 'Нет'}\n"
                    f"Бан: {'Да' if user.get('is_banned') else 'Нет'}\n"
                )
                await message.answer(reply, parse_mode="HTML")
                return
            else:
                await message.answer(f"Пользователь с ID {user_id} не найден")
                return
        
        # Если не ID, ищем по username и имени
        users = await get_all_users()
        if not users:
            await message.answer("Не удалось получить список пользователей.")
            return
        # Составляем список username и firstname/lastname
        candidates = []
        for u in users:
            uname = (u.get('username') or '').lower()
            fname = (u.get('firstname') or '').lower()
            lname = (u.get('lastname') or '').lower()
            full = f"{fname} {lname}".strip()
            candidates.append((u, uname, full))
        # Считаем похожесть
        scored = []
        for u, uname, full in candidates:
            score = max(
                difflib.SequenceMatcher(None, query.lower(), uname).ratio(),
                difflib.SequenceMatcher(None, query.lower(), full).ratio()
            )
            scored.append((score, u))
        scored.sort(reverse=True, key=lambda x: x[0])
        top = [u for score, u in scored if score > 0.3][:5]
        if not top:
            await message.answer("Пользователь не найден. Попробуйте другую часть ника или ID пользователя.")
            return
        reply = "<b>Похожие пользователи:</b>\n\n"
        for u in top:
            reply += (
                f"ID: <code>{u['id']}</code>\n"
                f"Username: @{format_username(u.get('username'))}\n"
                f"Имя: {u.get('firstname', '')} {u.get('lastname', '')}\n"
                f"Баланс: {u.get('balance', 'N/A')}\n"
                f"Уровень: {u.get('level', 'N/A')}\n"
                f"Админ: {'Да' if u.get('is_admin') else 'Нет'}\n"
                f"Бан: {'Да' if u.get('is_banned') else 'Нет'}\n"
                "----------------------\n"
            )
        await message.answer(reply, parse_mode="HTML")

    def format_queue_message(posts, title="Очередь постов"):
        import os
        from aiogram.utils.formatting import TextLink
        offers_chat_id = os.getenv("OFFERS_CHAT_ID")
        if offers_chat_id and offers_chat_id.startswith('-100'):
            offers_chat_id_link = offers_chat_id[4:]
        else:
            offers_chat_id_link = offers_chat_id or ''
        content = []
        content.append(Bold(f"📋 {title}\n"))
        content.append(Text("\n"))
        content.append(Text(f"Всего в очереди: {len(posts)} постов\n"))
        content.append(Text(f"Время запроса: {datetime.now(timezone(timedelta(hours=3))).strftime('%d.%m.%Y в %H:%M')}\n"))
        content.append(Text("\n"))
        for i, post in enumerate(posts, 1):
            author_id = post.get('author', 'N/A')
            content_text = post.get('content', '')
            posted_at_str = post.get('posted_at', 'N/A')
            post_id = post.get('id', 'N/A')
            telegram_id = post.get('telegram_id', 'N/A')
            try:
                if posted_at_str and ('+' in posted_at_str or 'Z' in posted_at_str):
                    posted_dt = datetime.strptime(posted_at_str.replace('Z', '+0000'), "%Y-%m-%dT%H:%M:%S%z")
                    posted_dt = posted_dt.astimezone(timezone(timedelta(hours=3)))
                    formatted_time = posted_dt.strftime('%d.%m.%Y в %H:%M')
                    now = datetime.now(timezone(timedelta(hours=3)))
                    time_diff = (posted_dt - now).total_seconds()
                    if time_diff > 0:
                        hours = int(time_diff // 3600)
                        minutes = int((time_diff % 3600) // 60)
                        if hours > 0:
                            time_until = f"через {hours}ч {minutes}м"
                        else:
                            time_until = f"через {minutes}м"
                        status_emoji = "⏳"
                    else:
                        time_until = "готов к публикации"
                        status_emoji = "✅"
                else:
                    formatted_time = posted_at_str
                    time_until = "неизвестно"
                    status_emoji = "❓"
            except Exception as e:
                formatted_time = posted_at_str
                time_until = "ошибка парсинга"
                status_emoji = "❌"
            content_preview = content_text[:80] + '...' if len(content_text) > 80 else content_text
            if not content_preview.strip():
                content_preview = Italic("Контент не найден")
            else:
                content_preview = Text(content_preview)
            content.append(Bold(f"{i}. {status_emoji} Пост #{post_id}\n"))
            content.append(Text(f"👤 Автор: {author_id}\n"))
            content.append(Text("📝 Контент: ") + content_preview + Text("\n"))
            content.append(Text(f"⏰ Время публикации: {formatted_time}\n"))
            content.append(Text(f"🕐 Статус: {time_until}\n"))
            # Формируем ссылку на сообщение по telegram_id
            if offers_chat_id_link and telegram_id != 'N/A':
                msg_link = f"https://t.me/c/{offers_chat_id_link}/{telegram_id}"
                content.append(Text("🆔 Telegram ID: ") + TextLink(str(telegram_id), url=msg_link) + Text("\n"))
            else:
                content.append(Text(f"🆔 Telegram ID: {telegram_id}\n"))
            content.append(Text("━━━━━━━━━━━━━━━━━━━━\n"))
            content.append(Text("\n"))  # Пустая строка между постами
        # Информация о следующем посте
        if posts:
            first_post = posts[0]
            first_post_time = first_post.get('posted_at')
            if first_post_time:
                try:
                    if '+' in first_post_time or 'Z' in first_post_time:
                        first_dt = datetime.strptime(first_post_time.replace('Z', '+0000'), "%Y-%m-%dT%H:%M:%S%z")
                        first_dt = first_dt.astimezone(timezone(timedelta(hours=3)))
                        now = datetime.now(timezone(timedelta(hours=3)))
                        time_to_first = (first_dt - now).total_seconds()
                        if time_to_first > 0:
                            hours = int(time_to_first // 3600)
                            minutes = int((time_to_first % 3600) // 60)
                            if hours > 0:
                                next_post_info = f"через {hours}ч {minutes}м"
                            else:
                                next_post_info = f"через {minutes}м"
                        else:
                            next_post_info = "готов к публикации"
                        content.append(Bold("📊 Информация:\n"))
                        content.append(Text(f"• Следующий пост: {next_post_info}\n"))
                        content.append(Text(f"• Интервал между постами: {POST_INTERVAL_MINUTES} минут\n"))
                        content.append(Text(f"• Неактивное время: 01:00-10:00 (посты переносятся на 10:00)\n"))
                        content.append(Text("\n"))
                except:
                    pass
        return ExpandableBlockQuote(*content)

    @dp.message(Command("queue"))
    async def queue_handler(message: types.Message):
        """Показывает подробную информацию о всех постах в очереди"""
        if not await is_admin(message.from_user.id):
            await message.answer("<b>У вас нет прав для выполнения этой команды</b>")
            return
        queue_info = await get_queue_info()
        if 'error' in queue_info:
            await message.answer(f"<b>Ошибка получения очереди:</b> {queue_info['error']}", parse_mode='HTML')
            return
        posts = queue_info.get('results', [])
        if not posts:
            await message.answer("<b>📋 Очередь постов</b>\n\n<blockquote>Очередь пуста — нет запланированных постов</blockquote>", parse_mode="HTML")
            return
        queue_message = format_queue_message(posts, title="Очередь постов")
        await message.answer(**queue_message.as_kwargs())

    @dp.message(Command("queueupdate"))
    async def queueupdate_handler(message: types.Message):
        """Принудительно пересчитывает все времена для постов в очереди"""
        if not await is_admin(message.from_user.id):
            await message.answer("<b>У вас нет прав для выполнения этой команды</b>")
            return
        try:
            result = await recalculate_queue_after_immediate_publication()
            if 'error' in result:
                await message.answer(f"<b>Ошибка пересчета очереди:</b> {result['error']}", parse_mode='HTML')
                return
            queue_info = await get_queue_info()
            if 'error' not in queue_info:
                posts = queue_info.get('results', [])
                if posts:
                    queue_message = format_queue_message(posts, title="Обновленная очередь постов")
                    await message.answer(**queue_message.as_kwargs())
        except Exception as e:
            logging.exception(f"[queueupdate_handler] Exception: {e}")
            await message.answer(f"❌ Произошла ошибка при пересчете очереди: {str(e)}", parse_mode='HTML')

    @dp.message(Command("makeadmin"))
    async def makeadmin_handler(message: types.Message):
        """Устанавливает права администратора пользователю (доступно только суперадмину)"""
        # Проверяем, что команду выполняет суперадмин
        if message.from_user.id != 914029246:
            await message.answer("❌ У вас нет прав для выполнения этой команды")
            return
        
        if not message.text:
            await message.answer("Использование: /makeadmin <user_id>")
            return
        parts = message.text.split()
        if len(parts) < 2:
            await message.answer("Использование: /makeadmin <user_id>")
            return
        user_id = parts[1]
        if not user_id.isdigit():
            await message.answer("ID пользователя должен быть числом")
            return
        user_id = int(user_id)
        
        # Получаем информацию о пользователе
        user_info = await get_user_info(user_id)
        if 'error' in user_info:
            error_text = user_info.get('error', '')
            if '404' in error_text:
                await message.answer(f'<b>Пользователь с ID {user_id} не существует.</b>', parse_mode='HTML')
            else:
                await message.answer(f'<b>Ошибка получения информации о пользователе:</b> {error_text}', parse_mode='HTML')
            return
        
        username = user_info.get('username', 'N/A') or user_info.get('firstname', 'N/A')
        
        # Устанавливаем права администратора через API
        headers = {'Content-Type': 'application/json'}
        API_URL = f"http://backend:8000/api/users/{user_id}/"
        update_data = {'is_admin': True}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.patch(API_URL, headers=headers, json=update_data) as response:
                    if response.status == 200:
                        result = await response.json()
                        await message.answer(
                            f"✅ <b>Права администратора установлены!</b>\n\n"
                            f"👤 <b>Пользователь:</b> {username} (ID: {user_id})\n"
                            f"⏰ <b>Время:</b> {datetime.now(timezone(timedelta(hours=3))).strftime('%d.%m.%Y в %H:%M')}\n"
                            f"👮 <b>Суперадмин:</b> {message.from_user.username or message.from_user.first_name}",
                            parse_mode="HTML"
                        )
                    else:
                        error_text = await response.text()
                        await message.answer(f"❌ Ошибка установки прав: {response.status} - {error_text}", parse_mode='HTML')
        except Exception as e:
            logging.error(f"[makeadmin_handler] Exception: {e}")
            await message.answer(f"❌ Произошла ошибка при установке прав: {str(e)}", parse_mode='HTML')

def format_username(username):
    if not username or str(username).lower() == 'none':
        return 'N/A'
    return username