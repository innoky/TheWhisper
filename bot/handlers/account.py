from aiogram import types, F, Dispatcher
from aiogram.enums import ParseMode
from db.wapi import get_user_info, get_user_pseudo_names, update_user_info
import logging

def register_account_handlers(dp: Dispatcher):
    @dp.message(F.text == "/account")
    async def account_handler(message: types.Message):
        user_id = message.from_user.id
        current_username = message.from_user.username
        current_firstname = message.from_user.first_name
        current_lastname = message.from_user.last_name
        
        # Получаем информацию о пользователе
        user_info = await get_user_info(user_id)
        if isinstance(user_info, dict) and user_info.get("error"):
            # Если пользователь не найден, создаем его
            logging.info(f"[account_handler] User {user_id} not found, creating new user")
            from db.wapi import try_create_user
            create_result = await try_create_user(user_id, current_username, current_firstname, current_lastname)
            if isinstance(create_result, dict) and create_result.get("error"):
                await message.answer(f'❌ Ошибка создания пользователя: {create_result["error"]}')
                return
            # Получаем информацию о созданном пользователе
            user_info = await get_user_info(user_id)
            if isinstance(user_info, dict) and user_info.get("error"):
                await message.answer(f'❌ Ошибка получения данных: {user_info["error"]}')
                return
        
        # Проверяем, нужно ли обновить данные пользователя
        needs_update = False
        if (user_info.get('username') != current_username or 
            user_info.get('firstname') != current_firstname or 
            user_info.get('lastname') != current_lastname):
            needs_update = True
            logging.info(f"[account_handler] User data changed, updating user {user_id}")
            logging.info(f"[account_handler] Old: username={user_info.get('username')}, firstname={user_info.get('firstname')}, lastname={user_info.get('lastname')}")
            logging.info(f"[account_handler] New: username={current_username}, firstname={current_firstname}, lastname={current_lastname}")
            
            # Обновляем данные пользователя
            update_result = await update_user_info(user_id, current_username, current_firstname, current_lastname)
            if not isinstance(update_result, dict) or not update_result.get("error"):
                logging.info(f"[account_handler] User data updated successfully")
                # Получаем обновленную информацию
                user_info = await get_user_info(user_id)
                if isinstance(user_info, dict) and user_info.get("error"):
                    await message.answer(f'❌ Ошибка получения обновленных данных: {user_info["error"]}')
                    return
            else:
                logging.error(f"[account_handler] Failed to update user data: {update_result}")
        else:
            logging.info(f"[account_handler] User data is up to date for user {user_id}")
        
        # Получаем список купленных ников
        user_pseudos = await get_user_pseudo_names(user_id)
        if isinstance(user_pseudos, dict) and user_pseudos.get("error"):
            await message.answer(f'❌ Ошибка получения ников: {user_pseudos["error"]}')
            return
        
        # Формируем красивый текст аккаунта
        account_text = f"""
<b>Профиль пользователя</b>

<b>Основная информация:</b>
• ID: {user_info.get('id', 'N/A')}
• Имя: {user_info.get('firstname', 'N/A')} {user_info.get('lastname', 'N/A')}
• Username: @{user_info.get('username', 'N/A')}
• Уровень: {user_info.get('level', 1)}/10
• Баланс: {user_info.get('balance', 0)} т.
• Статус: {'Заблокирован' if user_info.get('is_banned', False) else 'Активен'}

<b>Псевдонимы ({len(user_pseudos)}):</b>
"""
        
        # Если есть купленные ники, показываем их
        if user_pseudos:
            account_text += "\n<b>📋 Ваши никнеймы:</b>\n"
            # Получаем полную информацию о никах
            from db.wapi import get_all_pseudo_names
            all_pseudos = await get_all_pseudo_names()
            if not isinstance(all_pseudos, dict) or not all_pseudos.get("error"):
                pseudo_map = {p['id']: p for p in all_pseudos}
                total_spent = 0
                for pseudo_id in user_pseudos:
                    if pseudo_id in pseudo_map:
                        pseudo = pseudo_map[pseudo_id]
                        try:
                            price = float(pseudo.get('price', 0))
                        except (ValueError, TypeError):
                            price = 0.0
                        total_spent += price
                        account_text += f"• <code>{pseudo['pseudo']}</code> (💰 {price} т.)\n"
                
                account_text += f"\n<b>💸 Общая сумма покупок:</b> {total_spent} т."
            else:
                account_text += "• Информация о никнеймах временно недоступна\n"
        else:
            account_text += "\n<blockquote>У вас пока нет купленных никнеймов.\nИспользуйте /market для покупки!</blockquote>"
        
        await message.answer(account_text, parse_mode=ParseMode.HTML)

    @dp.message(F.text == "/help")
    async def help_handler(message: types.Message):
        help_text = """
<b>Справка по командам</b>

<b>Основные команды:</b>
• /start — запуск бота
• /account — профиль и баланс токенов
• /help — эта справка

<b>Магазин псевдонимов:</b>
• /market — покупка псевдонимов для анонимных комментариев

<b>Комментарии:</b>
• Отправьте ссылку на пост с параметром для оставления анонимного комментария

<b>Предложка постов:</b>
• Отправьте пост в чат для рассмотрения администрацией

<b>Подсказка:</b>
Используйте /account для просмотра баланса токенов и купленных псевдонимов
"""
        await message.answer(help_text, parse_mode=ParseMode.HTML) 