from aiogram import types, F, Dispatcher
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from db.wapi import ban_user, unban_user, add_pseudo_name, add_balance, set_balance, get_all_pseudo_names, deactivate_pseudo_name, set_user_level, get_user_info, get_active_posts_count, get_recent_posts, get_all_users, get_queue_info, recalculate_queue_after_immediate_publication, get_user_pseudo_names_full, get_comments_count, get_comments_for_user_posts, get_post_info
import re
from aiogram.methods import EditMessageReplyMarkup
import aiohttp
import logging
from datetime import datetime, timezone, timedelta
import os
import difflib
from aiogram.utils.formatting import ExpandableBlockQuote, Bold, Text, Italic, TextLink, Underline, Code, Pre, BlockQuote
from collections import Counter

# Импортируем константы из suggest
POST_INTERVAL_MINUTES = 30

async def format_queue_message(posts):
    if not posts:
        return Text("<b>Очередь пуста</b>")
    blocks = []
    offers_chat_id = os.getenv("OFFERS_CHAT_ID", "")
    if offers_chat_id and str(offers_chat_id).startswith("-100"):
        offers_chat_id = str(offers_chat_id)[4:]
    for i, post in enumerate(posts, 1):
        author_id = post.get('author', 'N/A')
        username = post.get('author_username', None)
        if not username or username == 'N/A':
            if author_id != 'N/A':
                user_info = await get_user_info(author_id)
                username = user_info.get('username', 'N/A') if user_info and not user_info.get('error') else 'N/A'
            else:
                username = 'N/A'
        content = post.get('content', '')[:100]
        post_id = post.get('id', 'N/A')
        telegram_id = post.get('telegram_id')
        msg_link = None
        if offers_chat_id and telegram_id:
            msg_link = f"https://t.me/c/{offers_chat_id}/{telegram_id}"
        blocks.append(
            Bold(f"#{i}") + Text(": ") +
            (TextLink(Bold(f"ID {author_id}"), url=msg_link) if msg_link else Bold(f"ID {author_id}")) +
            Text(" | ") + Italic(f"@{username}") + Text("\n") +
            Text(f"{content}...") + Text("\n") +
            Code(f"ID поста: {post_id}") + Text("\n") +
            (Text("Пост в предложке: ") + TextLink(f"{telegram_id}", url=msg_link) if msg_link else Text("Пост в предложке: N/A")) + Text("\n\n")
        )
    return ExpandableBlockQuote(*blocks)

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
        from collections import Counter
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
        # --- Интересные факты о комментариях ---
        comments = await get_comments_for_user_posts(user_id)
        comments_count = len(comments)
        # Среднее число комментариев на пост
        avg_comments = round(comments_count / total, 2) if total > 0 else 0
        # --- Синтаксический анализ: топ-слова пользователя ---
        import re
        from collections import Counter
        stopwords = set([
            'и', 'в', 'во', 'не', 'что', 'он', 'на', 'я', 'с', 'со', 'как', 'а', 'то', 'все', 'она', 'так', 'его',
            'но', 'да', 'ты', 'к', 'у', 'же', 'вы', 'за', 'бы', 'по', 'только', 'ее', 'мне', 'было', 'вот', 'от',
            'меня', 'еще', 'нет', 'о', 'из', 'ему', 'теперь', 'когда', 'даже', 'ну', 'вдруг', 'ли', 'если', 'уже',
            'или', 'ни', 'быть', 'был', 'него', 'до', 'вас', 'нибудь', 'опять', 'уж', 'вам', 'ведь', 'там', 'потом',
            'себя', 'ничего', 'ей', 'может', 'они', 'тут', 'где', 'есть', 'надо', 'ней', 'для', 'мы', 'тебя', 'их',
            'чем', 'была', 'сам', 'чтоб', 'без', 'будто', 'чего', 'раз', 'тоже', 'себе', 'под', 'будет', 'ж', 'тогда',
            'кто', 'этот', 'того', 'потому', 'этого', 'какой', 'совсем', 'ним', 'здесь', 'этом', 'один', 'почти',
            'мой', 'тем', 'чтобы', 'нее', 'сейчас', 'были', 'куда', 'зачем', 'всех', 'никогда', 'можно', 'при',
            'наконец', 'два', 'об', 'другой', 'хоть', 'после', 'над', 'больше', 'тот', 'через', 'эти', 'нас', 'про',
            'всего', 'них', 'какая', 'много', 'разве', 'три', 'эту', 'моя', 'впрочем', 'хорошо', 'свою', 'этой',
            'перед', 'иногда', 'лучше', 'чуть', 'том', 'нельзя', 'такой', 'им', 'более', 'всегда', 'конечно',
            'всю', 'между'
        ])
        all_text = ' '.join(p.get('content', '') for p in posts if p.get('content'))
        all_text = re.sub(r'https?://\S+', '', all_text)
        all_text = re.sub(r'[^а-яА-Яa-zA-ZёЁ\s]', ' ', all_text)
        all_text = all_text.lower()
        words = [w for w in all_text.split() if len(w) > 3 and w not in stopwords]
        word_counter = Counter(words)
        top_words = word_counter.most_common(10)
        # Формируем красивый вывод
        firstname = user_info.get('firstname', '') or ''
        lastname = user_info.get('lastname', '') or ''
        username = user_info.get('username', None)
        name_line = f"<b>Статистика: {firstname}{(' ' + lastname) if lastname and lastname != 'N/A' else ''}</b>\n"
        if username and username != 'N/A':
            name_line += f"<i>@{username}</i>\n"
        name_line += "\n"
        # Блок 'О вас'
        about_block = ""
        if reg_dt and days_with_us is not None:
            about_block += f"<b>С нами:</b> <u>{days_with_us} дней</u>\n"
        about_block += f"<b>Уровень:</b> {user_info.get('level','N/A')}\n"
        about_block += f"<b>Баланс:</b> {user_info.get('balance','N/A')} т.\n"
        about_block += f"<b>Псевдонимы:</b> {pseudos_str}\n"
        about_block += "\n"
        # Блок 'Ваши посты'
        posts_block = "<b>Ваши посты:</b>\n"
        posts_block += f"<b>Всего:</b> {total}\n"
        posts_block += f"<b>Опубликовано:</b> {posted}\n"
        posts_block += f"<b>Отклонено:</b> {rejected}\n"
        posts_block += f"<b>В очереди:</b> {queued}\n"
        posts_block += "\n"
        # Топ-3 длинных поста
        top_block = ""
        if top_posts_str:
            top_block += '<b>🏆 Топ-3 самых длинных поста:</b>\n'
            for i, p in enumerate(top_posts, 1):
                frag = p.get('content','')[:120].replace('\n',' ')
                top_block += f"<blockquote>{i}. {frag}{'...' if len(p.get('content',''))>120 else ''} ({len(p.get('content',''))} симв.)</blockquote>\n"
        # Первая работа
        first_block = ""
        if first_post_str:
            first_block += f"<b>Первая работа</b>\n<blockquote>{first_post_str}</blockquote>\n"
        # Топ-слова
        words_block = ""
        if top_words:
            words_block += '\n<b>Топ-слова ваших постов:</b>\n'
            words_block += ', '.join(f'{w} ({c})' for w, c in top_words)
            words_block += '\n'
        # Финальный вывод
        stats_message = name_line + about_block + posts_block + top_block + first_block + words_block
        stats_message += "\n<i>Спасибо за активность! Продолжай щитпостить и зарабатывать токены!</i>"
        await message.answer(stats_message, parse_mode="HTML")

    @dp.message(Command("queue"))
    async def queue_handler(message: types.Message):
        offers_chat_id = os.getenv("OFFERS_CHAT_ID")
        admin_chat_id = os.getenv("ADMIN_CHAT_ID")
        allowed_ids = {str(offers_chat_id), str(admin_chat_id)}
        if str(message.chat.id) not in allowed_ids:
            return
        queue_info = await get_queue_info()
        if queue_info.get("error"):
            await message.answer("<b>Ошибка получения очереди:</b> {}".format(queue_info['error']), parse_mode="HTML")
            return
        text = await format_queue_message(queue_info.get("results", []))
        if isinstance(text, Text) and str(text) == "<b>Очередь пуста</b>":
            await message.answer(str(text), parse_mode="HTML", disable_web_page_preview=True)
        else:
            await message.answer(**text.as_kwargs(), disable_web_page_preview=True)

    @dp.message(Command("queueupdate"))
    async def queueupdate_handler(message: types.Message):
        offers_chat_id = os.getenv("OFFERS_CHAT_ID")
        admin_chat_id = os.getenv("ADMIN_CHAT_ID")
        allowed_ids = {str(offers_chat_id), str(admin_chat_id)}
        if str(message.chat.id) not in allowed_ids:
            return
        result = await recalculate_queue_after_immediate_publication()
        if result.get("error"):
            await message.answer(f"<b>Ошибка пересчета очереди:</b> {result['error']}", parse_mode="HTML")
            return
        await message.answer(f"<b>Очередь пересчитана:</b> {result.get('message', 'Готово')}", parse_mode="HTML")
        queue_info = await get_queue_info()
        text = await format_queue_message(queue_info.get("results", []))
        if isinstance(text, Text) and str(text) == "<b>Очередь пуста</b>":
            await message.answer(str(text), parse_mode="HTML", disable_web_page_preview=True)
        else:
            await message.answer(**text.as_kwargs(), disable_web_page_preview=True)

    @dp.message(Command("getuser"))
    async def getuser_handler(message: types.Message):
        # Проверка чата
        offers_chat_id = os.getenv("OFFERS_CHAT_ID")
        admin_chat_id = os.getenv("ADMIN_CHAT_ID")
        allowed_ids = {str(offers_chat_id), str(admin_chat_id)}
        if str(message.chat.id) not in allowed_ids:
            return
        
        # Парсим аргумент
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            await message.answer("Использование: /getuser <user_id или username>")
            return
        query = parts[1].strip().lstrip('@')
        user = None
        all_users = await get_all_users()
        found_by = None
        # Поиск по ID
        if query.isdigit():
            user = await get_user_info(int(query))
            if user and not user.get('error'):
                found_by = 'id'
        # Поиск по username (точное совпадение)
        if not user or user.get('error'):
            for u in all_users:
                if (u.get('username') or '').lower() == query.lower():
                    user = u
                    found_by = 'username'
                    break
        # Поиск по username с опечатками (Левенштейн)
        if not user:
            usernames = [(u, (u.get('username') or '')) for u in all_users]
            similar = [(u, difflib.SequenceMatcher(None, (uname).lower(), query.lower()).ratio()) for u, uname in usernames if uname]
            similar = sorted(similar, key=lambda x: x[1])
            if similar and similar[0][1] > 0.6:
                user = similar[0][0]
                found_by = 'username_levenshtein'
        # Если не найдено
        if not user or user.get('error'):
            # Предложить похожие
            usernames = [u.get('username', '') or '' for u in all_users]
            matches = difflib.get_close_matches(query, usernames, n=5, cutoff=0.4)
            if matches:
                await message.answer(f"Пользователь не найден. Возможно, вы имели в виду: " + ", ".join([f"@{m}" for m in matches]))
            else:
                await message.answer("Пользователь не найден.")
            return
        # Получаем расширенную инфу (купленные ники)
        user_id = user.get('id')
        pseudos = await get_user_pseudo_names_full(user_id) if user_id else []
        pseudos_str = ', '.join([p[1] for p in pseudos]) if pseudos else 'Нет'
        # Формируем ответ
        info = f"<b>Информация о пользователе</b>\n"
        info += f"<b>ID:</b> {user.get('id', 'N/A')}\n"
        info += f"<b>Username:</b> @{user.get('username', 'N/A')}\n"
        info += f"<b>Имя:</b> {user.get('firstname', 'N/A')} {user.get('lastname', '')}\n"
        info += f"<b>Уровень:</b> {user.get('level', 'N/A')}\n"
        info += f"<b>Баланс:</b> {user.get('balance', 'N/A')} т.\n"
        info += f"<b>Псевдонимы:</b> {pseudos_str}\n"
        info += f"<b>Забанен:</b> {'Да' if user.get('is_banned') else 'Нет'}\n"
        info += f"<b>Админ:</b> {'Да' if user.get('is_admin') else 'Нет'}\n"
        info += f"<b>Дата регистрации:</b> {user.get('created_at', 'N/A')}\n"
        if found_by == 'levenshtein':
            info += f"\n<i>⚠️ Найден по похожему username</i>"
        await message.answer(info, parse_mode="HTML")

