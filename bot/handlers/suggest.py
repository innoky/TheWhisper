from aiogram import types, F, Dispatcher
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode, ContentType
from datetime import datetime, timedelta, timezone
import os
import pytz
from datetime import time
from db.wapi import get_last_post, try_create_post, mark_post_as_posted, mark_post_as_rejected_by_telegram_id, get_post_by_telegram_id, process_post_payment, get_user_info, get_active_posts_count, publish_post_now, get_last_published_post_time, recalculate_queue_after_immediate_publication
from SugQueue import publish_to_channel, update_post_channel_info, send_publication_notification
import logging


ACTIVE_START_HOUR = 10  # 10:00
ACTIVE_END_HOUR = 1     # 01:00 следующего дня
POST_INTERVAL_MINUTES = 30
BOT_NAME = os.getenv("BOT_NAME")

async def send_submission_notification(bot, user_id: int, post_content: str):
    """Отправляет красивое уведомление пользователю о том, что пост отправлен на рассмотрение"""
    try:
        # Формируем красивое сообщение
        notification_text = f"📤 <b>Пост отправлен на рассмотрение!</b>\n\n"
        notification_text += f"📝 <b>Содержание поста:</b>\n"
        notification_text += f"<i>«{post_content[:150]}{'...' if len(post_content) > 150 else ''}»</i>\n\n"
        notification_text += f"⏰ <b>Время отправки:</b> {datetime.now(timezone(timedelta(hours=3))).strftime('%d.%m.%Y в %H:%M')}\n\n"
        notification_text += f"📋 <b>Что дальше:</b>\n"
        notification_text += f"• Администраторы рассмотрят ваш пост\n"
        notification_text += f"• Вы получите уведомление о решении\n"
        notification_text += f"• При одобрении пост будет опубликован в канале\n\n"
        notification_text += f"⏳ <b>Ожидайте уведомления о результате!</b>\n\n"
        notification_text += f"💡 <b>Пока ждете:</b>\n"
        notification_text += f"• Изучите /help - правила и команды\n"
        notification_text += f"• Посетите /market - магазин псевдонимов\n"
        notification_text += f"• Подготовьте новые посты"
        
        # Отправляем уведомление
        await bot.send_message(
            chat_id=user_id,
            text=notification_text,
            parse_mode="HTML"
        )
        logging.info(f"[send_submission_notification] Beautiful submission notification sent to user {user_id}")
        
    except Exception as e:
        logging.error(f"[send_submission_notification] Error sending submission notification: {e}")


async def send_rejection_notification(bot, user_id: int, post_content: str):
    """Отправляет красивое уведомление пользователю об отклонении поста"""
    try:
        # Формируем красивое сообщение об отклонении
        notification_text = f"❌ <b>Ваш пост отклонен</b>\n\n"
        notification_text += f"📝 <b>Содержание поста:</b>\n"
        notification_text += f"<i>«{post_content[:150]}{'...' if len(post_content) > 150 else ''}»</i>\n\n"
        notification_text += f"💡 <b>Возможные причины:</b>\n"
        notification_text += f"• Пост не соответствует правилам сообщества\n"
        notification_text += f"• Содержание не подходит для канала\n"
        notification_text += f"• Дублирование существующего контента\n\n"
        notification_text += f"🔄 <b>Что делать:</b>\n"
        notification_text += f"• Пересмотрите содержание поста\n"
        notification_text += f"• Убедитесь, что пост соответствует тематике\n"
        notification_text += f"• Попробуйте отправить новый пост\n\n"
        notification_text += f"📚 <b>Полезные команды:</b>\n"
        notification_text += f"• /help - получить справку\n"
        notification_text += f"• /market - купить псевдонимы\n\n"
        notification_text += f"⏰ <b>Время отклонения:</b> {datetime.now(timezone(timedelta(hours=3))).strftime('%d.%m.%Y в %H:%M')}"
        
        # Отправляем уведомление
        await bot.send_message(
            chat_id=user_id,
            text=notification_text,
            parse_mode="HTML"
        )
        logging.info(f"[send_rejection_notification] Beautiful rejection notification sent to user {user_id}")
        
    except Exception as e:
        logging.error(f"[send_rejection_notification] Error sending rejection notification: {e}")


async def send_approval_notification(bot, user_id: int, post_content: str, scheduled_time: datetime, queue_position: int = None):
    """Отправляет красивое уведомление пользователю об одобрении поста"""
    try:
        # Формируем красивое сообщение
        notification_text = f"🎉 <b>Ваш пост одобрен!</b>\n\n"
        notification_text += f"📝 <b>Содержание поста:</b>\n"
        notification_text += f"<i>«{post_content[:150]}{'...' if len(post_content) > 150 else ''}»</i>\n\n"
        
        scheduled_time_str = scheduled_time.strftime("%d.%m.%Y в %H:%M")
        time_diff = (scheduled_time - datetime.now(timezone(timedelta(hours=3)))).total_seconds() / 60
        
        if queue_position and queue_position > 1:
            notification_text += f"📋 <b>Статус:</b> Пост добавлен в очередь\n"
            notification_text += f"📍 <b>Позиция в очереди:</b> #{queue_position}\n"
            notification_text += f"⏰ <b>Время публикации:</b> {scheduled_time_str}\n"
            if time_diff > 0:
                notification_text += f"⏳ <b>Ожидание:</b> {time_diff:.0f} минут\n"
            else:
                notification_text += f"🚀 <b>Публикация:</b> Моментально\n"
        else:
            if time_diff > 0:
                notification_text += f"⏰ <b>Статус:</b> Пост запланирован\n"
                notification_text += f"📅 <b>Время публикации:</b> {scheduled_time_str}\n"
                notification_text += f"⏳ <b>Ожидание:</b> {time_diff:.0f} минут\n"
            else:
                notification_text += f"🚀 <b>Статус:</b> Пост будет опубликован моментально\n"
                notification_text += f"📅 <b>Время публикации:</b> {scheduled_time_str}\n"
        
        notification_text += f"\n💰 <b>Награда:</b> После публикации вы получите токены за пост!\n"
        notification_text += f"💡 <b>Совет:</b> Используйте токены для покупки псевдонимов в /market\n\n"
        notification_text += f"🎯 <b>Следующий шаг:</b> Ожидайте уведомления о публикации!"
        
        # Отправляем уведомление
        await bot.send_message(
            chat_id=user_id,
            text=notification_text,
            parse_mode="HTML"
        )
        logging.info(f"[send_approval_notification] Beautiful approval notification sent to user {user_id}")
        
    except Exception as e:
        logging.error(f"[send_approval_notification] Error sending approval notification: {e}")


async def send_publication_and_payment_notification(bot, user_id: int, post_content: str, tokens_added: int, new_balance: str, channel_message_id: int):
    """Отправляет красивое объединенное уведомление о публикации и оплате"""
    try:
        # Формируем ссылку на пост в канале
        channel_id = os.getenv("CHANNEL_ID")
        if not channel_id:
            logging.error(f"[send_publication_and_payment_notification] CHANNEL_ID not set")
            return
            
        if channel_id.startswith('-100'):
            channel_id = channel_id[4:]  # Убираем префикс -100 для ссылки
        
        post_link = f"https://t.me/c/{channel_id}/{channel_message_id}"
        
        # Формируем красивое объединенное сообщение
        notification_text = f"🎉 <b>Ваш пост опубликован и оплачен!</b>\n\n"
        notification_text += f"📝 <b>Содержание:</b>\n"
        notification_text += f"<i>«{post_content[:150]}{'...' if len(post_content) > 150 else ''}»</i>\n\n"
        notification_text += f"🔗 <b>Ссылка на пост:</b>\n"
        notification_text += f"<a href=\"{post_link}\">📱 Открыть пост в канале</a>\n\n"
        notification_text += f"💰 <b>Награда за пост:</b>\n"
        notification_text += f"➕ <b>Получено токенов:</b> +{tokens_added} т.\n"
        notification_text += f"📊 <b>Новый баланс:</b> {new_balance} т.\n\n"
        notification_text += f"⏰ <b>Время публикации:</b> {datetime.now(timezone(timedelta(hours=3))).strftime('%d.%m.%Y в %H:%M')}\n\n"
        notification_text += f"🎯 <b>Что дальше:</b>\n"
        notification_text += f"• Используйте токены для покупки псевдонимов в /market\n"
        notification_text += f"• Создавайте новые посты для получения токенов\n"
        notification_text += f"• Участвуйте в жизни сообщества\n\n"
        notification_text += f"🎉 <b>Спасибо за качественный контент!</b> 🌟"
        
        # Отправляем уведомление
        await bot.send_message(
            chat_id=user_id,
            text=notification_text,
            parse_mode="HTML",
            disable_web_page_preview=True
        )
        logging.info(f"[send_publication_and_payment_notification] Beautiful combined notification sent to user {user_id}")
        
    except Exception as e:
        logging.error(f"[send_publication_and_payment_notification] Error sending combined notification: {e}")


def save_post_to_db(user_id: int, text: str):
    # Заглушка под сохранение в БД
    print(f"[DB] Saved post from {user_id}: {text[:30]}...")


def get_content_type_and_text(message: types.Message) -> tuple[str, str]:
    """
    Определяет тип контента сообщения и возвращает соответствующий текст для БД
    """
    if message.text:
        return "text", message.text.strip()
    elif message.photo:
        caption = message.caption or ""
        return "photo", f"[PHOTO] {caption}".strip()
    elif message.animation:
        caption = message.caption or ""
        return "gif", f"[GIF] {caption}".strip()
    elif message.sticker:
        return "sticker", "[STICKER]"
    elif message.video:
        caption = message.caption or ""
        return "video", f"[VIDEO] {caption}".strip()
    elif message.voice:
        return "voice", "[VOICE]"
    elif message.audio:
        caption = message.caption or ""
        return "audio", f"[AUDIO] {caption}".strip()
    elif message.document:
        caption = message.caption or ""
        return "document", f"[DOCUMENT] {caption}".strip()
    else:
        return "unknown", "[UNKNOWN CONTENT]"


def register_suggest_handler(dp: Dispatcher):
    @dp.message()
    async def suggest_handler(message: types.Message, state: FSMContext):
        if message.from_user and message.from_user.first_name == "Telegram":
            comment_url = f"https://t.me/{BOT_NAME}?start={message.message_id}"
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="💬 Комментировать", url=comment_url)]
                ]
            )
            await message.reply(
                "💬 <b>Теперь вы можете оставить анонимный комментарий к этому посту тут:</b>",
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
        elif message.chat.type == 'private':
            # Получаем тип контента и текст для БД
            content_type, post_content = get_content_type_and_text(message)
            
            msg = await message.copy_to(os.getenv('OFFERS_CHAT_ID'))
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{message.from_user.id}")],
                    [InlineKeyboardButton(text="✅ Добавить", callback_data=f"approve_{message.from_user.id}")]
                ]
            )
            await message.bot.send_message(
                chat_id=os.getenv("OFFERS_CHAT_ID"),
                text=(
                    f"id: {message.from_user.id}\n"
                    f"username: @{message.from_user.username or 'N/A'}\n"
                    f"content_type: {content_type}\n\n"
                ),
                reply_to_message_id=msg.message_id,
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
            
            # Отправляем уведомление пользователю о том, что пост отправлен на рассмотрение
            await send_submission_notification(message.bot, message.from_user.id, post_content)

    @dp.callback_query(F.data.startswith(("reject_",)))
    async def reject_callback(callback: types.CallbackQuery):
        user_id = int(callback.data.split("_")[1])
        original_msg = callback.message.reply_to_message
        
        # Получаем тип контента и текст для БД
        content_type, post_content = get_content_type_and_text(original_msg)
        
        # Проверяем, есть ли пост в очереди
        post_info = await get_post_by_telegram_id(original_msg.message_id)
        
        if 'error' not in post_info:
            # Пост есть в очереди, удаляем его
            result = await mark_post_as_rejected_by_telegram_id(original_msg.message_id)
            logging.info(f"[reject_callback] Post removed from queue: {result}")
        else:
            # Поста нет в очереди, просто отклоняем
            logging.info(f"[reject_callback] Post not in queue, just rejecting")
        
        # Формируем сообщение об отклонении для админ чата
        admin_message_text = f"❌ <b>Пост отклонен!</b>\n\n"
        admin_message_text += f"👤 <b>Автор:</b> {user_id}\n"
        admin_message_text += f"📝 <b>Содержание:</b> {post_content[:100]}{'...' if len(post_content) > 100 else ''}\n"
        admin_message_text += f"📄 <b>Тип контента:</b> {content_type}\n\n"
        admin_message_text += f"⏰ <b>Время отклонения:</b> {datetime.now(timezone(timedelta(hours=3))).strftime('%d.%m.%Y в %H:%M')}\n"
        admin_message_text += f"👮 <b>Админ:</b> {callback.from_user.username or callback.from_user.first_name}"
        
        # Редактируем сообщение в админ чате
        await callback.message.edit_text(
            text=admin_message_text,
            parse_mode="HTML"
        )
        
        await callback.answer("Пост отклонён!")
        
        # Отправляем уведомление об отклонении
        await send_rejection_notification(callback.bot, user_id, post_content)

    @dp.callback_query(F.data.startswith(("approve_",)))
    async def approve_callback(callback: types.CallbackQuery):
        user_id = int(callback.data.split("_")[1])
        original_msg = callback.message.reply_to_message
        moscow_tz = pytz.timezone('Europe/Moscow')
        now = datetime.now(timezone(timedelta(hours=3)))
        
        # Проверяем количество активных постов в очереди
        active_posts_count = await get_active_posts_count()
        logging.info(f"[approve_callback] Active posts in queue: {active_posts_count}")
        
        # Если есть очередь, рассчитываем время относительно последнего поста в очереди
        if active_posts_count > 0:
            logging.info(f"[approve_callback] Queue exists ({active_posts_count} posts), calculating from last queued post")
            # Получаем время последнего поста в очереди для планирования
            last_post_data = await get_last_post()
            last_post_time_str = last_post_data.get('posted_at')
            
            try:
                if last_post_time_str and ('+' in last_post_time_str or 'Z' in last_post_time_str):
                    last_post_dt = datetime.strptime(last_post_time_str.replace('Z', '+0000'), "%Y-%m-%dT%H:%M:%S%z")
                    last_post_dt = last_post_dt.astimezone(moscow_tz)
                else:
                    last_post_dt = moscow_tz.localize(datetime.strptime(last_post_time_str, "%Y-%m-%d %H:%M:%S")) if last_post_time_str else now
            except ValueError as e:
                last_post_dt = now
                
            # Планируем через 30 минут от последнего поста в очереди
            scheduled_time = last_post_dt + timedelta(minutes=POST_INTERVAL_MINUTES)
            
            # Проверяем активное время
            if scheduled_time.hour < ACTIVE_START_HOUR and scheduled_time.hour >= ACTIVE_END_HOUR:
                next_day = now.date() + timedelta(days=1)
                scheduled_time = moscow_tz.localize(datetime.combine(next_day, time(hour=ACTIVE_START_HOUR, minute=0)))
        else:
            # Очереди нет, проверяем время последнего опубликованного поста
            last_published_data = await get_last_published_post_time()
            
            if 'error' in last_published_data:
                # Постов вообще нет, публикуем моментально
                logging.info(f"[approve_callback] No published posts exist, publishing immediately")
                scheduled_time = now
            else:
                # Есть последний опубликованный пост, используем его channel_posted_at
                last_post_time_str = last_published_data.get('channel_posted_at')
                
                logging.info(f"[approve_callback] Last published post channel_posted_at: {last_post_time_str}")
                
                try:
                    if last_post_time_str and ('+' in last_post_time_str or 'Z' in last_post_time_str):
                        last_post_dt = datetime.strptime(last_post_time_str.replace('Z', '+0000'), "%Y-%m-%dT%H:%M:%S%z")
                        last_post_dt = last_post_dt.astimezone(moscow_tz)
                    else:
                        last_post_dt = moscow_tz.localize(datetime.strptime(last_post_time_str, "%Y-%m-%d %H:%M:%S"))
                    
                    time_since_last_post = (now - last_post_dt).total_seconds() / 60  # в минутах
                    logging.info(f"[approve_callback] Time since last published post: {time_since_last_post:.1f} minutes")
                    
                    if time_since_last_post >= POST_INTERVAL_MINUTES:
                        # Прошло больше 30 минут, публикуем моментально
                        logging.info(f"[approve_callback] More than {POST_INTERVAL_MINUTES} minutes passed, publishing immediately")
                        scheduled_time = now
                    else:
                        # Прошло меньше 30 минут, ждем остаток
                        remaining_minutes = POST_INTERVAL_MINUTES - time_since_last_post
                        scheduled_time = now + timedelta(minutes=remaining_minutes)
                        logging.info(f"[approve_callback] Less than {POST_INTERVAL_MINUTES} minutes passed, waiting {remaining_minutes:.1f} more minutes")
                        
                except ValueError as e:
                    logging.error(f"[approve_callback] Error parsing last published post time: {e}")
                    scheduled_time = now
        
        # Получаем тип контента и текст для БД
        content_type, post_content = get_content_type_and_text(original_msg)
        
        if not post_content:
            logging.error(f"[approve_callback] Не удалось создать пост: контент пустой. user_id={user_id}, telegram_id={original_msg.message_id}")
            await callback.answer("Ошибка: контент поста пустой!")
            return
        
        logging.info(f"[approve_callback] try_create_post payload: author_id={user_id}, content={post_content}, telegram_id={original_msg.message_id}, post_time={scheduled_time}")
        create_result = await try_create_post(author_id=user_id, content=post_content, telegram_id=original_msg.message_id, post_time=scheduled_time)
        
        if 'error' in create_result:
            logging.error(f"[approve_callback] Error creating post: {create_result['error']}")
            await callback.answer("Ошибка создания поста!")
            return
        
        # Форматируем время для отображения
        scheduled_time_str = scheduled_time.strftime("%d.%m.%Y в %H:%M")
        time_diff = (scheduled_time - now).total_seconds() / 60
        
        # Формируем информативное сообщение для попапа
        if active_posts_count > 0:
            status_message = f"📋 Пост добавлен в очередь!\n\n"
            status_message += f"📍 Позиция в очереди: {active_posts_count + 1}\n"
            status_message += f"⏰ Время публикации: {scheduled_time_str}\n"
            if time_diff > 0:
                status_message += f"⏳ Ожидание: {time_diff:.0f} минут\n"
            else:
                status_message += f"🚀 Публикация: Моментально\n"
        else:
            if time_diff > 0:
                status_message = f"⏰ Пост запланирован!\n\n"
                status_message += f"📅 Время публикации: {scheduled_time_str}\n"
                status_message += f"⏳ Ожидание: {time_diff:.0f} минут\n"
            else:
                status_message = f"🚀 Пост будет опубликован моментально!\n\n"
                status_message += f"📅 Время публикации: {scheduled_time_str}\n"
        
        # Создаем новую клавиатуру с кнопкой немедленной публикации
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{user_id}")],
                [InlineKeyboardButton(text="🚀 Опубликовать сейчас", callback_data=f"publish_now_{user_id}")]
            ]
        )
        
        # Формируем информативное сообщение для админ чата
        admin_message_text = f"✅ <b>Пост одобрен!</b>\n\n"
        admin_message_text += f"👤 <b>Автор:</b> {user_id}\n"
        admin_message_text += f"📝 <b>Содержание:</b> {post_content[:100]}{'...' if len(post_content) > 100 else ''}\n"
        admin_message_text += f"📄 <b>Тип контента:</b> {content_type}\n\n"
        
        if active_posts_count > 0:
            admin_message_text += f"📋 <b>Статус:</b> Добавлен в очередь\n"
            admin_message_text += f"📍 <b>Позиция в очереди:</b> {active_posts_count + 1}\n"
            admin_message_text += f"⏰ <b>Время публикации:</b> {scheduled_time_str}\n"
            if time_diff > 0:
                admin_message_text += f"⏳ <b>Ожидание:</b> {time_diff:.0f} минут\n"
            else:
                admin_message_text += f"🚀 <b>Публикация:</b> Моментально\n"
        else:
            if time_diff > 0:
                admin_message_text += f"⏰ <b>Статус:</b> Запланирован\n"
                admin_message_text += f"📅 <b>Время публикации:</b> {scheduled_time_str}\n"
                admin_message_text += f"⏳ <b>Ожидание:</b> {time_diff:.0f} минут\n"
            else:
                admin_message_text += f"🚀 <b>Статус:</b> Будет опубликован моментально\n"
                admin_message_text += f"📅 <b>Время публикации:</b> {scheduled_time_str}\n"
        
        admin_message_text += f"\n⏰ <b>Время одобрения:</b> {datetime.now(timezone(timedelta(hours=3))).strftime('%d.%m.%Y в %H:%M')}\n"
        admin_message_text += f"👮 <b>Админ:</b> {callback.from_user.username or callback.from_user.first_name}"
        
        # Редактируем сообщение в админ чате
        await callback.message.edit_text(
            text=admin_message_text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        
        await callback.answer(status_message)
        
        # Отправляем уведомление об одобрении пользователю
        queue_position = active_posts_count + 1 if active_posts_count > 0 else None
        await send_approval_notification(callback.bot, user_id, post_content, scheduled_time, queue_position)

    @dp.callback_query(F.data.startswith(("publish_now_",)))
    async def publish_now_callback(callback: types.CallbackQuery):
        """Обработчик кнопки 'Опубликовать сейчас' - немедленно публикует пост и оплачивает его"""
        user_id = int(callback.data.split("_")[2])
        original_msg = callback.message.reply_to_message
        
        # Сразу отвечаем на callback, чтобы избежать timeout
        await callback.answer("🚀 Публикуем пост...")
        
        try:
            logging.info(f"[publish_now_callback] Processing immediate publication for user_id={user_id}, telegram_id={original_msg.message_id}")
            
            # Получаем информацию о посте по telegram_id
            post_info = await get_post_by_telegram_id(original_msg.message_id)
            if 'error' in post_info:
                logging.error(f"[publish_now_callback] Post not found: {post_info['error']}")
                # Отправляем сообщение об ошибке в чат
                await callback.message.answer("❌ Ошибка: пост не найден в базе данных")
                return
            
            logging.info(f"[publish_now_callback] Found post: {post_info}")
            
            # Проверяем, что пост еще не опубликован
            if post_info.get('is_posted', False):
                await callback.message.answer("❌ Пост уже опубликован!")
                return
            
            # Проверяем, что пост еще не оплачен
            if post_info.get('is_paid', False):
                await callback.message.answer("❌ Пост уже оплачен!")
                return
            
            # Немедленно публикуем пост и обрабатываем оплату
            publish_result = await publish_post_now(post_info['id'])
            
            if 'error' in publish_result:
                logging.error(f"[publish_now_callback] Publication failed: {publish_result['error']}")
                await callback.message.answer(f"❌ Ошибка публикации: {publish_result['error']}")
                return
            
            logging.info(f"[publish_now_callback] Publication successful: {publish_result}")
            
            # Получаем информацию о выплаченных токенах
            tokens_added = publish_result.get('tokens_added', 0)
            author_level = publish_result.get('author_level', 1)
            
            # Публикуем в канал
            success, channel_message_id = await publish_to_channel(post_info, callback.bot)
            if not success:
                await callback.message.answer("❌ Ошибка публикации в канал")
                return
            
            # Обновляем информацию о канале
            await update_post_channel_info(post_info['id'], channel_message_id)
            
            # Пересчитываем очередь после моментальной публикации
            queue_recalc_result = await recalculate_queue_after_immediate_publication()
            if 'error' in queue_recalc_result:
                logging.warning(f"[publish_now_callback] Queue recalculation failed: {queue_recalc_result['error']}")
            else:
                logging.info(f"[publish_now_callback] Queue recalculated: {queue_recalc_result.get('message', 'Success')}")
            
            logging.info(f"[publish_now_callback] Successfully published and paid post {post_info['id']}: level {author_level}, {tokens_added} tokens")
            
            # Отправляем объединенное уведомление о публикации и оплате
            await send_publication_and_payment_notification(callback.bot, user_id, post_info.get('content', ''), tokens_added, publish_result.get('author_balance', 'N/A'), channel_message_id)
            
            # Убираем кнопки и показываем результат
            await callback.message.delete_reply_markup()
            
            # Формируем сообщение о публикации для админ чата
            admin_message_text = f"🚀 <b>Пост опубликован и оплачен!</b>\n\n"
            admin_message_text += f"👤 <b>Автор:</b> {user_id}\n"
            admin_message_text += f"📝 <b>Содержание:</b> {post_info.get('content', '')[:100]}{'...' if len(post_info.get('content', '')) > 100 else ''}\n\n"
            admin_message_text += f"💰 <b>Оплата:</b>\n"
            admin_message_text += f"📊 <b>Уровень автора:</b> {author_level}\n"
            admin_message_text += f"➕ <b>Токенов выплачено:</b> {tokens_added}\n"
            admin_message_text += f"📈 <b>Новый баланс автора:</b> {publish_result.get('author_balance', 'N/A')} т.\n\n"
            admin_message_text += f"📝 <b>ID поста:</b> {post_info['id']}\n"
            admin_message_text += f"📅 <b>Время публикации:</b> {datetime.now(timezone(timedelta(hours=3))).strftime('%d.%m.%Y в %H:%M')}\n"
            admin_message_text += f"👮 <b>Админ:</b> {callback.from_user.username or callback.from_user.first_name}"
            
            # Редактируем сообщение в админ чате
            await callback.message.edit_text(
                text=admin_message_text,
                parse_mode="HTML"
            )
            
        except Exception as e:
            logging.exception(f"[publish_now_callback] Exception processing immediate publication for user_id={user_id}")
            await callback.message.answer("❌ Произошла ошибка при публикации")

    @dp.callback_query(F.data.startswith(("pay_",)))
    async def pay_callback(callback: types.CallbackQuery):
        """Обработчик кнопки 'Выплатить' - выплачивает токены на основе уровня автора"""
        user_id = int(callback.data.split("_")[1])
        original_msg = callback.message.reply_to_message
        
        try:
            logging.info(f"[pay_callback] Processing payment for user_id={user_id}, telegram_id={original_msg.message_id}")
            
            # Получаем информацию о посте по telegram_id (ID оригинального сообщения пользователя)
            post_info = await get_post_by_telegram_id(original_msg.message_id)
            if 'error' in post_info:
                logging.error(f"[pay_callback] Post not found: {post_info['error']}")
                await callback.answer("❌ Ошибка: пост не найден в базе данных")
                return
            
            logging.info(f"[pay_callback] Found post: {post_info}")
            
            # Проверяем, что пост еще не оплачен
            if post_info.get('is_paid', False):
                await callback.answer("❌ Пост уже оплачен!")
                return
            
            # Проверяем, что пост выложен в канал
            channel_message_id = post_info.get('channel_message_id')
            if not channel_message_id:
                await callback.answer("❌ Пост еще не выложен в канал")
                return
            
            # Получаем информацию об авторе поста
            author_id = post_info.get('author')
            if not author_id:
                await callback.answer("❌ Ошибка: у поста нет автора")
                return
            
            # Получаем информацию об авторе для определения уровня
            author_info = await get_user_info(author_id)
            if 'error' in author_info:
                await callback.answer("❌ Ошибка: не удалось получить информацию об авторе")
                return
            
            author_level = author_info.get('level', 1)
            logging.info(f"[pay_callback] Author level: {author_level}")
            
            # Обрабатываем оплату через API
            payment_result = await process_post_payment(post_info['id'])
            
            if 'error' in payment_result:
                logging.error(f"[pay_callback] Payment processing failed: {payment_result['error']}")
                await callback.answer(f"❌ Ошибка обработки оплаты: {payment_result['error']}")
                return
            
            logging.info(f"[pay_callback] Payment processed successfully: {payment_result}")
            
            # Получаем информацию о выплаченных токенах
            tokens_added = payment_result.get('tokens_added', 0)
            
            # Формируем сообщение об оплате для админ чата
            admin_message_text = f"💰 <b>Пост оплачен!</b>\n\n"
            admin_message_text += f"👤 <b>Автор:</b> {author_id}\n"
            admin_message_text += f"📝 <b>Содержание:</b> {post_info.get('content', '')[:100]}{'...' if len(post_info.get('content', '')) > 100 else ''}\n\n"
            admin_message_text += f"💰 <b>Оплата:</b>\n"
            admin_message_text += f"📊 <b>Уровень автора:</b> {author_level}\n"
            admin_message_text += f"➕ <b>Токенов выплачено:</b> {tokens_added}\n"
            admin_message_text += f"📈 <b>Новый баланс автора:</b> {payment_result.get('author_balance', 'N/A')} т.\n\n"
            admin_message_text += f"📝 <b>ID поста:</b> {post_info['id']}\n"
            admin_message_text += f"📅 <b>Время выплаты:</b> {datetime.now(timezone(timedelta(hours=3))).strftime('%d.%m.%Y в %H:%M')}\n"
            admin_message_text += f"👮 <b>Админ:</b> {callback.from_user.username or callback.from_user.first_name}"
            
            # Редактируем сообщение в админ чате
            await callback.message.edit_text(
                text=admin_message_text,
                parse_mode="HTML"
            )
            
            await callback.answer(
                f"✅ Оплата обработана!\n\n"
                f"👤 Автор: {author_id}\n"
                f"📊 Уровень автора: {author_level}\n"
                f"💰 Токенов выплачено: {tokens_added}\n"
                f"📈 Новый баланс автора: {payment_result.get('author_balance', 'N/A')} т.\n"
                f"📝 ID поста: {post_info['id']}\n"
                f"📅 Время выплаты: {datetime.now(timezone(timedelta(hours=3))).strftime('%d.%m.%Y в %H:%M')}\n"
                f"👮 Админ: {callback.from_user.username or callback.from_user.first_name}"
            )
            
            logging.info(f"[pay_callback] Successfully processed payment for post {post_info['id']}: level {author_level}, {tokens_added} tokens")
            
            # Уведомление о пополнении баланса уже отправлено в объединенном уведомлении
            
        except Exception as e:
            logging.exception(f"[pay_callback] Exception processing payment for user_id={user_id}")
            await callback.answer("❌ Произошла ошибка при обработке оплаты")