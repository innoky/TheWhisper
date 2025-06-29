from aiogram import types, Dispatcher
from aiogram.filters import Command
from aiogram.enums import ParseMode
import os
from datetime import datetime, timezone, timedelta


def register_help_handlers(dp: Dispatcher):
    @dp.message(Command("help"))
    async def help_handler(message: types.Message):
        """Показывает справку по командам в зависимости от типа чата"""
        
        # Проверяем, что это админский чат
        admin_chat_id = os.getenv("ADMIN_CHAT_ID")
        is_admin_chat = admin_chat_id and str(message.chat.id) == str(admin_chat_id)
        
        if is_admin_chat:
            # Админская справка
            help_message = f"<b>Админская справка</b>\n\n"
            help_message += f"<b>Дата:</b> {datetime.now(timezone(timedelta(hours=3))).strftime('%d.%m.%Y в %H:%M')}\n"
            help_message += f"<b>Админ:</b> {message.from_user.username or message.from_user.first_name}\n\n"
            
            help_message += f"<b>Управление постами:</b>\n"
            help_message += f"• Добавить — пост в очередь публикации\n"
            help_message += f"• Отклонить — отклонение поста\n"
            help_message += f"• Опубликовать сейчас — немедленная публикация и оплата\n"
            help_message += f"• <code>/queue</code> — просмотр очереди постов\n"
            help_message += f"• <code>/queueupdate</code> — пересчет времени публикации\n"
            help_message += f"• <code>/stats</code> — статистика системы\n"
            
            # Добавляем команду makeadmin только для суперадмина
            if message.from_user.id == 914029246:
                help_message += f"• <code>/makeadmin &lt;user_id&gt;</code> — установка прав администратора\n"
            
            help_message += f"\n<b>Управление пользователями:</b>\n"
            help_message += f"• <code>/unban &lt;user_id&gt;</code> — разблокировка\n"
            help_message += f"• <code>/levelup &lt;user_id&gt;</code> — повышение уровня (макс. 10)\n"
            help_message += f"• <code>/leveldown &lt;user_id&gt;</code> — понижение уровня (мин. 1)\n"
            help_message += f"• <code>/getuser &lt;username&gt;</code> — поиск пользователя\n\n"
            
            help_message += f"<b>Управление балансом:</b>\n"
            help_message += f"• <code>/addbalance &lt;user_id&gt; &lt;сумма&gt;</code> — добавление токенов\n"
            help_message += f"• <code>/setbalance &lt;user_id&gt; &lt;сумма&gt;</code> — установка баланса\n\n"
            
            help_message += f"<b>Управление псевдонимами:</b>\n"
            help_message += f"• <code>/addpseudo \"&lt;имя&gt;\" &lt;цена&gt;</code> — создание псевдонима\n"
            help_message += f"• <code>/allpseudos</code> — список всех псевдонимов\n"
            help_message += f"• <code>/deactivate &lt;pseudo_id&gt;</code> — деактивация псевдонима\n\n"
            
            help_message += f"<b>Система автопостинга:</b>\n"
            help_message += f"• Публикация каждые 30 минут\n"
            help_message += f"• Неактивное время: 01:00-10:00\n"
            help_message += f"• Моментальная публикация при пустой очереди\n\n"
            
            help_message += f"<b>Уровни токенов:</b> 50-500 за пост (зависит от уровня)"
            
        else:
            # Обычная справка для пользователей
            help_message = f"<b>Справка по командам</b>\n\n"
            help_message += f"<b>Основные функции:</b>\n"
            help_message += f"<blockquote>• Отправка постов для публикации\n"
            help_message += f"• Анонимные комментарии через псевдонимы\n"
            help_message += f"• Система токенов за качественный контент</blockquote>\n\n"
            
            help_message += f"<b>Доступные команды:</b>\n"
            help_message += f"• <code>/account</code> — профиль и баланс токенов\n"
            help_message += f"• <code>/market</code> — магазин псевдонимов\n"
            help_message += f"• <code>/help</code> — эта справка\n\n"
            
            help_message += f"<b>Система токенов:</b>\n"
            help_message += f"<blockquote>• 50-500 токенов за пост (зависит от уровня)\n"
            help_message += f"• Токены используются для покупки псевдонимов\n"
            help_message += f"• Уровень устанавливается администрацией</blockquote>\n\n"
            
            help_message += f"<b>Псевдонимы:</b>\n"
            help_message += f"<blockquote>• Уникальные имена для анонимных комментариев\n"
            help_message += f"• Покупка через /market за токены\n"
            help_message += f"• Использование при комментировании постов</blockquote>\n\n"
            
            help_message += f"<b>Поддержка:</b> @rmnvin"
        
        await message.answer(help_message, parse_mode="HTML") 