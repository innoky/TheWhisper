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
            help_message = f"🤖 <b>Справка по админским командам</b>\n\n"
            help_message += f"📅 <b>Дата:</b> {datetime.now(timezone(timedelta(hours=3))).strftime('%d.%m.%Y в %H:%M')}\n"
            help_message += f"👮 <b>Админ:</b> {message.from_user.username or message.from_user.first_name}\n\n"
            
            help_message += f"📝 <b>Управление постами:</b>\n"
            help_message += f"• <b>Кнопка 'Добавить'</b> - добавляет пост в очередь с информацией о времени публикации\n"
            help_message += f"• <b>Кнопка 'Отклонить'</b> - отклоняет пост (бан через кнопку)\n"
            help_message += f"• <b>Кнопка 'Опубликовать сейчас'</b> - немедленно публикует и оплачивает пост\n"
            help_message += f"• <code>/queue</code> - показывает все посты в очереди\n"
            help_message += f"• <code>/queueupdate</code> - принудительно пересчитывает время для всех постов в очереди\n"
            help_message += f"• <code>/stats</code> - статистика постов\n"
            
            # Добавляем команду makeadmin только для суперадмина
            if message.from_user.id == 914029246:
                help_message += f"• <code>/makeadmin &lt;user_id&gt;</code> - устанавливает права администратора\n"
            
            help_message += f"\n👥 <b>Управление пользователями:</b>\n"
            help_message += f"• <code>/unban &lt;user_id&gt;</code> - разблокирует пользователя\n"
            help_message += f"• <code>/levelup &lt;user_id&gt;</code> - повышает уровень пользователя (макс. 10)\n"
            help_message += f"• <code>/leveldown &lt;user_id&gt;</code> - понижает уровень пользователя (мин. 1)\n"
            help_message += f"• <code>/getuser &lt;username&gt;</code> - поиск пользователя по нику (неточное совпадение)\n\n"
            
            help_message += f"💰 <b>Управление балансом:</b>\n"
            help_message += f"• <code>/addbalance &lt;user_id&gt; &lt;сумма&gt;</code> - добавляет токены к балансу\n"
            help_message += f"• <code>/setbalance &lt;user_id&gt; &lt;сумма&gt;</code> - устанавливает баланс\n\n"
            
            help_message += f"🏷️ <b>Управление псевдонимами:</b>\n"
            help_message += f"• <code>/addpseudo \"&lt;никнейм&gt;\" &lt;цена&gt;</code> - добавляет псевдоним\n"
            help_message += f"• <code>/allpseudos</code> - показывает все псевдонимы со статистикой\n"
            help_message += f"• <code>/deactivate &lt;pseudo_id&gt;</code> - деактивирует псевдоним\n\n"
            
            help_message += f"📊 <b>Информация:</b>\n"
            help_message += f"• <code>/stats</code> - показывает статистику системы\n"
            help_message += f"• <code>/help</code> - показывает эту справку\n\n"
            
            help_message += f"💡 <b>Примеры использования:</b>\n"
            help_message += f"• <code>/addbalance 123456 50.5</code> - добавить 50.5 токенов пользователю 123456\n"
            help_message += f"• <code>/addpseudo \"Ядерный шепот\" 150</code> - создать псевдоним за 150 токенов\n"
            help_message += f"• <code>/levelup 123456</code> - повысить уровень пользователя 123456\n\n"
            
            help_message += f"⚙️ <b>Система автопостинга:</b>\n"
            help_message += f"• Посты публикуются каждые 30 минут\n"
            help_message += f"• Неактивное время: 01:00-10:00 (посты переносятся на 10:00)\n"
            help_message += f"• Если очередь пуста и прошло &gt;30 мин - публикация моментальная\n"
            help_message += f"• Если прошло &lt;30 мин - ждем остаток времени\n\n"
            
            help_message += f"🎯 <b>Уровни пользователей:</b>\n"
            help_message += f"• Уровень 1: 5 токенов за пост\n"
            help_message += f"• Уровень 2: 10 токенов за пост\n"
            help_message += f"• ... и так далее до уровня 10: 50 токенов за пост"
            
        else:
            # Обычная справка для пользователей
            help_message = f"🤖 <b>Справка по командам</b>\n\n"
            help_message += f"👋 <b>Добро пожаловать в ядерный бот!</b>\n\n"
            
            help_message += f"📝 <b>Отправка постов:</b>\n"
            help_message += f"• Просто отправьте пост в этот чат\n"
            help_message += f"• Администрация рассмотрит и опубликует\n"
            help_message += f"• За каждый пост вы получаете токены\n\n"
            
            help_message += f"💬 <b>Анонимные комментарии:</b>\n"
            help_message += f"• Перейдите по ссылке из поста\n"
            help_message += f"• Оставьте комментарий анонимно\n"
            help_message += f"• Используйте купленные псевдонимы\n\n"
            
            help_message += f"📋 <b>Доступные команды:</b>\n"
            help_message += f"• <code>/account</code> - ваш профиль и баланс токенов\n"
            help_message += f"• <code>/market</code> - магазин псевдонимов\n"
            help_message += f"• <code>/help</code> - эта справка\n\n"
            
            help_message += f"💰 <b>Система токенов:</b>\n"
            help_message += f"• За каждый пост: 5-50 токенов (зависит от уровня)\n"
            help_message += f"• Токены можно тратить на псевдонимы\n"
            help_message += f"• Уровень повышается администрацией\n\n"
            
            help_message += f"🏷️ <b>Псевдонимы:</b>\n"
            help_message += f"• Покупайте в магазине за токены\n"
            help_message += f"• Используйте для анонимных комментариев\n"
            help_message += f"• Каждый псевдоним уникален\n\n"
            
            help_message += f"📞 <b>Поддержка:</b>\n"
            help_message += f"• Обращайтесь к администрации\n"
            help_message += f"• Соблюдайте правила сообщества"
        
        await message.answer(help_message, parse_mode="HTML") 