from aiogram import types, F, Dispatcher
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from db.wapi import ban_user, unban_user, add_pseudo_name, add_balance, set_balance, get_all_pseudo_names, deactivate_pseudo_name, set_user_level, get_user_info, get_active_posts_count, get_recent_posts, get_all_users, get_queue_info, recalculate_queue_after_immediate_publication
import re
from aiogram.methods import EditMessageReplyMarkup
import aiohttp
import logging
from datetime import datetime, timezone, timedelta
import os
import difflib

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
            await callback.bot(EditMessageReplyMarkup(chat_id=msg.chat.id, message_id=msg.message_id, reply_markup=None))
        
        # Формируем информативное сообщение
        if 'error' in result:
            ban_message = f"❌ <b>Ошибка при бане пользователя!</b>\n\n"
            ban_message += f"👤 <b>Пользователь:</b> {username} (ID: {user_id})\n"
            ban_message += f"🚫 <b>Ошибка:</b> {result['error']}"
        else:
            ban_message = f"🚫 <b>Пользователь забанен!</b>\n\n"
            ban_message += f"👤 <b>Пользователь:</b> {username} (ID: {user_id})\n"
            ban_message += f"⏰ <b>Время:</b> {datetime.now(timezone(timedelta(hours=3))).strftime('%d.%m.%Y в %H:%M')}\n"
            ban_message += f"👮 <b>Админ:</b> {callback.from_user.username or callback.from_user.first_name}"
        
        await callback.answer(ban_message, show_alert=True)
    
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
            unban_message += f"👮 <b>Админ:</b> {message.from_user.username or message.from_user.first_name}"
        
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
            await message.answer(f"<b>Ошибка:</b> {user_info['error']}")
            return
        
        current_level = int(user_info.get('level', 1))
        new_level = min(current_level + 1, 10)  # Не больше 10
        
        if new_level == current_level:
            await message.answer(f"❌ Пользователь {user_id} уже имеет максимальный уровень (10)")
            return
        
        # Устанавливаем новый уровень
        result = await set_user_level(user_id, new_level)
        if 'error' in result:
            await message.answer(f"❌ Ошибка при повышении уровня: {result['error']}")
            return
        
        await message.answer(f"<b>Уровень пользователя {user_id} повышен с {current_level} до {new_level}</b>")
        
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
            await message.answer(f"<b>Ошибка:</b> {user_info['error']}")
            return
        
        current_level = int(user_info.get('level', 1))
        new_level = max(current_level - 1, 1)  # Не меньше 1
        
        if new_level == current_level:
            await message.answer(f"❌ Пользователь {user_id} уже имеет минимальный уровень (1)")
            return
        
        # Устанавливаем новый уровень
        result = await set_user_level(user_id, new_level)
        if 'error' in result:
            await message.answer(f"❌ Ошибка при понижении уровня: {result['error']}")
            return
        
        await message.answer(f"<b>Уровень пользователя {user_id} понижен с {current_level} до {new_level}</b>")
        
        # Отправляем уведомление пользователю
        try:
            if message.bot:
                await message.bot.send_message(
                    chat_id=user_id,
                    text=f"<b>Ваш уровень понижен</b>\n\n"
                         f"Старый уровень: {current_level}\n"
                         f"Новый уровень: {new_level}\n\n"
                         f"За каждый пост вы получаете меньше токенов",
                    parse_mode="HTML"
                )
        except Exception as e:
            logging.warning(f"Could not send leveldown notification to user {user_id}: {e}")

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
            pseudo_message = f"<b>Псевдоним успешно добавлен</b>\n\n"
            pseudo_message += f"<b>Имя:</b> \"{nickname}\"\n"
            pseudo_message += f"<b>Цена:</b> {price:.2f} т.\n"
            pseudo_message += f"<b>ID:</b> {result['id']}\n"
            pseudo_message += f"<b>Статус:</b> Доступен для покупки\n"
            pseudo_message += f"<b>Время:</b> {datetime.now(timezone(timedelta(hours=3))).strftime('%d.%m.%Y в %H:%M')}\n"
            pseudo_message += f"<b>Админ:</b> {message.from_user.username or message.from_user.first_name}"
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
        
        user_id = int(user_id)
        
        # Получаем информацию о пользователе и текущий баланс
        user_info = await get_user_info(user_id)
        if 'error' in user_info:
            await message.answer(f'<b>Ошибка получения информации о пользователе:</b> {user_info["error"]}')
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
            balance_message += f"<b>Админ:</b> {message.from_user.username or message.from_user.first_name}"
        else:
            balance_message = f"<b>Ошибка обновления баланса</b>\n\n"
            balance_message += f"<b>Пользователь:</b> {username} (ID: {user_id})\n"
            balance_message += f"<b>Сумма:</b> {amount} т.\n"
            balance_message += f"<b>Ошибка:</b> {result}"
        
        await message.answer(balance_message, parse_mode="HTML")

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
        
        user_id = int(user_id)
        
        # Получаем информацию о пользователе и текущий баланс
        user_info = await get_user_info(user_id)
        if 'error' in user_info:
            await message.answer(f'<b>Ошибка получения информации о пользователе:</b> {user_info["error"]}')
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
            balance_message += f"<b>Админ:</b> {message.from_user.username or message.from_user.first_name}"
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
            await message.answer(f'<b>Ошибка:</b> {pseudos}')
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
            await message.answer('Использование: /deactivate pseudo_id')
            return
        parts = message.text.split()
        if len(parts) < 2 or not parts[1].isdigit():
            await message.answer('Использование: /deactivate pseudo_id')
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
            deactivate_message += f"<b>Админ:</b> {message.from_user.username or message.from_user.first_name}"
        else:
            deactivate_message = f"<b>Ошибка деактивации псевдонима</b>\n\n"
            deactivate_message += f"<b>Имя:</b> \"{pseudo_name}\"\n"
            deactivate_message += f"<b>ID:</b> {pseudo_id}\n"
            deactivate_message += f"<b>Ошибка:</b> {result}"
        
        await message.answer(deactivate_message, parse_mode="HTML")

    @dp.message(Command("stats"))
    async def stats_handler(message: types.Message):
        """Показывает статистику системы"""
        try:
            # Получаем статистику постов
            active_posts_count = await get_active_posts_count()
            posts_data = await get_recent_posts()
            
            # Подсчитываем общую статистику постов
            total_posts = 0
            posted_posts = 0
            rejected_posts = 0
            
            if isinstance(posts_data, dict) and 'results' in posts_data:
                posts = posts_data['results']
                total_posts = len(posts)
                posted_posts = sum(1 for p in posts if p.get('is_posted', False))
                rejected_posts = sum(1 for p in posts if p.get('is_rejected', False))
            
            # Получаем статистику псевдонимов
            pseudos = await get_all_pseudo_names()
            total_pseudos = 0
            available_pseudos = 0
            
            if isinstance(pseudos, list):
                total_pseudos = len(pseudos)
                available_pseudos = sum(1 for p in pseudos if p.get('is_available', False))
            
            # Формируем статистику
            stats_message = f"<b>Статистика системы</b>\n\n"
            stats_message += f"<b>Дата:</b> {datetime.now(timezone(timedelta(hours=3))).strftime('%d.%m.%Y в %H:%M')}\n\n"
            
            stats_message += f"<b>Посты:</b>\n"
            stats_message += f"Всего постов: {total_posts}\n"
            stats_message += f"Опубликовано: {posted_posts}\n"
            stats_message += f"Отклонено: {rejected_posts}\n"
            stats_message += f"В очереди: {active_posts_count}\n\n"
            
            stats_message += f"<b>Псевдонимы:</b>\n"
            stats_message += f"Всего псевдонимов: {total_pseudos}\n"
            stats_message += f"Доступно: {available_pseudos}\n"
            stats_message += f"Недоступно: {total_pseudos - available_pseudos}\n\n"
            
            # Добавляем информацию о системе
            stats_message += f"<b>Система:</b>\n"
            stats_message += f"Бот: Активен\n"
            stats_message += f"API: Работает\n"
            stats_message += f"Админ: {message.from_user.username or message.from_user.first_name}"
            
            await message.answer(stats_message, parse_mode="HTML")
            
        except Exception as e:
            error_message = f"<b>Ошибка получения статистики</b>\n\n"
            error_message += f"<b>Ошибка:</b> {str(e)}\n"
            error_message += f"<b>Время:</b> {datetime.now(timezone(timedelta(hours=3))).strftime('%d.%m.%Y в %H:%M')}"
            await message.answer(error_message, parse_mode="HTML")

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
                    f"Username: @{user.get('username') or 'N/A'}\n"
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
                f"Username: @{u.get('username') or 'N/A'}\n"
                f"Имя: {u.get('firstname', '')} {u.get('lastname', '')}\n"
                f"Баланс: {u.get('balance', 'N/A')}\n"
                f"Уровень: {u.get('level', 'N/A')}\n"
                f"Админ: {'Да' if u.get('is_admin') else 'Нет'}\n"
                f"Бан: {'Да' if u.get('is_banned') else 'Нет'}\n"
                "----------------------\n"
            )
        await message.answer(reply, parse_mode="HTML")

    @dp.message(Command("queue"))
    async def queue_handler(message: types.Message):
        """Показывает подробную информацию о всех постах в очереди"""
        if not await is_admin(message.from_user.id):
            await message.answer("<b>У вас нет прав для выполнения этой команды</b>")
            return
        
        queue_info = await get_queue_info()
        
        if 'error' in queue_info:
            await message.answer(f"<b>Ошибка получения очереди:</b> {queue_info['error']}")
            return
        
        posts = queue_info.get('results', [])
        count = len(posts)
        
        if count == 0:
            await message.answer("<b>📋 Очередь постов</b>\n\n<blockquote>Очередь пуста — нет запланированных постов</blockquote>", parse_mode="HTML")
            return
        
        # Формируем сообщение с подробной информацией о постах
        queue_message = f"<b>📋 Очередь постов</b>\n\n"
        queue_message += f"<b>Всего в очереди:</b> {count} постов\n"
        queue_message += f"<b>Время запроса:</b> {datetime.now(timezone(timedelta(hours=3))).strftime('%d.%m.%Y в %H:%M')}\n\n"
        
        for i, post in enumerate(posts, 1):
            author_id = post.get('author', 'N/A')
            content = post.get('content', '')
            posted_at_str = post.get('posted_at', 'N/A')
            post_id = post.get('id', 'N/A')
            telegram_id = post.get('telegram_id', 'N/A')
            
            # Парсим время публикации и рассчитываем время до публикации
            try:
                if posted_at_str and ('+' in posted_at_str or 'Z' in posted_at_str):
                    posted_dt = datetime.strptime(posted_at_str.replace('Z', '+0000'), "%Y-%m-%dT%H:%M:%S%z")
                    posted_dt = posted_dt.astimezone(timezone(timedelta(hours=3)))
                    formatted_time = posted_dt.strftime('%d.%m.%Y в %H:%M')
                    
                    # Рассчитываем время до публикации
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
            
            # Обрезаем контент для отображения
            content_preview = content[:80] + '...' if len(content) > 80 else content
            if not content_preview.strip():
                content_preview = "<i>Контент не найден</i>"
            
            queue_message += f"<b>{i}.</b> {status_emoji} <b>Пост #{post_id}</b>\n"
            queue_message += f"👤 <b>Автор:</b> {author_id}\n"
            queue_message += f"📝 <b>Контент:</b> {content_preview}\n"
            queue_message += f"⏰ <b>Время публикации:</b> {formatted_time}\n"
            queue_message += f"🕐 <b>Статус:</b> {time_until}\n"
            queue_message += f"🆔 <b>Telegram ID:</b> {telegram_id}\n"
            queue_message += f"━━━━━━━━━━━━━━━━━━━━\n\n"
        
        # Добавляем информацию о следующем посте
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
                        
                        queue_message += f"<b>📊 Информация:</b>\n"
                        queue_message += f"• Следующий пост: {next_post_info}\n"
                        queue_message += f"• Интервал между постами: {POST_INTERVAL_MINUTES} минут\n"
                        queue_message += f"• Неактивное время: 01:00-10:00 (посты переносятся на 10:00)\n"
                except:
                    pass
        
        await message.answer(queue_message, parse_mode="HTML")

    @dp.message(Command("queueupdate"))
    async def queueupdate_handler(message: types.Message):
        """Принудительно пересчитывает все времена для постов в очереди"""
        if not await is_admin(message.from_user.id):
            await message.answer("<b>У вас нет прав для выполнения этой команды</b>")
            return
        
        await message.answer("<b>Начинаю пересчет очереди...</b>")
        
        try:
            # Выполняем пересчет очереди
            result = await recalculate_queue_after_immediate_publication()
            
            if 'error' in result:
                await message.answer(f"<b>Ошибка пересчета очереди:</b> {result['error']}")
                return
            
            updated_count = result.get('updated_count', 0)
            status_message = result.get('message', 'Пересчет завершен')
            
            if updated_count == 0:
                await message.answer("<b>Очередь пуста — нечего пересчитывать</b>")
            else:
                await message.answer(f"<b>{status_message}</b>\n\n<b>Пересчитано постов:</b> {updated_count}")
                
                # Показываем обновленную очередь
                queue_info = await get_queue_info()
                if 'error' not in queue_info:
                    posts = queue_info.get('posts', [])
                    count = queue_info.get('count', 0)
                    
                    if count > 0:
                        queue_message = f"<b>Обновленная очередь постов</b>\n\n"
                        queue_message += f"<b>Всего в очереди:</b> {count} постов\n\n"
                        
                        for i, post in enumerate(posts, 1):
                            author_id = post.get('author', 'N/A')
                            content = post.get('content', '')[:50] + '...' if len(post.get('content', '')) > 50 else post.get('content', '')
                            posted_at_str = post.get('posted_at', 'N/A')
                            post_id = post.get('id', 'N/A')
                            
                            # Парсим время публикации
                            try:
                                if posted_at_str and ('+' in posted_at_str or 'Z' in posted_at_str):
                                    posted_dt = datetime.strptime(posted_at_str.replace('Z', '+0000'), "%Y-%m-%dT%H:%M:%S%z")
                                    posted_dt = posted_dt.astimezone(timezone(timedelta(hours=3)))
                                    formatted_time = posted_dt.strftime('%d.%m.%Y в %H:%M')
                                else:
                                    formatted_time = posted_at_str
                            except:
                                formatted_time = posted_at_str
                            
                            queue_message += f"<b>{i}.</b> 👤 <b>Автор:</b> {author_id}\n"
                            queue_message += f"📝 <b>Контент:</b> {content}\n"
                            queue_message += f"⏰ <b>Время публикации:</b> {formatted_time}\n"
                            queue_message += f"🆔 <b>ID поста:</b> {post_id}\n\n"
                        
                        await message.answer(queue_message, parse_mode="HTML")
                
        except Exception as e:
            logging.exception(f"[queueupdate_handler] Exception: {e}")
            await message.answer(f"❌ Произошла ошибка при пересчете очереди: {str(e)}")

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
            await message.answer(f"❌ Ошибка: {user_info['error']}")
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
                        await message.answer(f"❌ Ошибка установки прав: {response.status} - {error_text}")
        except Exception as e:
            logging.error(f"[makeadmin_handler] Exception: {e}")
            await message.answer(f"❌ Произошла ошибка при установке прав: {str(e)}")