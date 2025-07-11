from aiogram import types, F, Dispatcher
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, Message, InaccessibleMessage
from aiogram.enums import ParseMode, ContentType
from datetime import datetime, timedelta, timezone
import os
import pytz
from datetime import time
from db.wapi import get_last_post, try_create_post, mark_post_as_posted, mark_post_as_rejected_by_telegram_id, get_post_by_telegram_id, process_post_payment, get_user_info, get_active_posts_count, publish_post_now, get_last_published_post_time, recalculate_queue_after_immediate_publication, try_create_user, get_post_info
from SugQueue import publish_to_channel, update_post_channel_info, send_publication_notification
import logging
import re
from aiogram.fsm.state import State, StatesGroup


ACTIVE_START_HOUR = 10  # 10:00
ACTIVE_END_HOUR = 1     # 01:00 следующего дня
POST_INTERVAL_MINUTES = 15
BOT_NAME = os.getenv("ORACLE_BOT_NAME")

async def send_submission_notification(bot, user_id: int, post_content: str):
    """Отправляет уведомление пользователю о том, что пост отправлен на рассмотрение"""
    try:
        # Формируем сообщение
        notification_text = f"<b>Вопрос отправлен на рассмотрение</b>\n\n"
        notification_text += f"<b>Содержание:</b> «{post_content[:150]}{'...' if len(post_content) > 150 else ''}»\n\n"
        notification_text += f"<b>Время:</b> {datetime.now(timezone(timedelta(hours=3))).strftime('%d.%m.%Y в %H:%M')}\n\n"
        notification_text += f"<b>Процесс рассмотрения:</b>\n"
        notification_text += f"<blockquote>• Администрация проверит контент\n"
        notification_text += f"• Уведомление о решении\n"
        notification_text += f"• Публикация при одобрении</blockquote>\n\n"
        notification_text += f"Пока ожидаете: изучите /help и /market"
        
        # Отправляем уведомление
        await bot.send_message(
            chat_id=user_id,
            text=notification_text,
            parse_mode="HTML"
        )
        logging.info(f"[send_submission_notification] Submission notification sent to user {user_id}")
        
    except Exception as e:
        logging.error(f"[send_submission_notification] Error sending submission notification: {e}")


async def send_rejection_notification(bot, user_id: int, post_content: str):
    """Отправляет уведомление пользователю об отклонении поста"""
    try:
        # Формируем сообщение об отклонении
        notification_text = f"<b>Ваш вопрос отклонен</b>\n\n"
        notification_text += f"<b>Возможные причины:</b>\n"
        notification_text += f"<blockquote>• Пост не соответствует правилам сообщества\n"
        notification_text += f"• Содержание не подходит для канала\n"
        notification_text += f"• Дублирование существующего контента</blockquote>\n\n"
        notification_text += f"<b>Что делать:</b>\n"
        notification_text += f"<blockquote>• Пересмотрите содержание поста\n"
        notification_text += f"• Убедитесь, что пост соответствует тематике\n"
        notification_text += f"• Попробуйте отправить новый пост</blockquote>\n\n"
        notification_text += f"<b>Полезные команды:</b>\n"
        notification_text += f"• /help — получить справку\n"
        notification_text += f"• /market — купить псевдонимы\n\n"
        notification_text += f"<b>Время отклонения:</b> {datetime.now(timezone(timedelta(hours=3))).strftime('%d.%m.%Y в %H:%M')}"
        
        # Отправляем уведомление
        await bot.send_message(
            chat_id=user_id,
            text=notification_text,
            parse_mode="HTML"
        )
        logging.info(f"[send_rejection_notification] Rejection notification sent to user {user_id}")
        
    except Exception as e:
        logging.error(f"[send_rejection_notification] Error sending rejection notification: {e}")


async def send_approval_notification(bot, user_id: int, post_content: str, scheduled_time: datetime, queue_position: int = None):
    """Отправляет уведомление пользователю об одобрении поста"""
    try:
        # Формируем сообщение
        notification_text = f"<b>Ваш вопрос одобрен</b>\n\n"
        notification_text += f"<b>Содержание:</b> «{post_content[:150]}{'...' if len(post_content) > 150 else ''}»\n\n"
        
        scheduled_time_str = scheduled_time.strftime("%d.%m.%Y в %H:%M")
        time_diff = (scheduled_time - datetime.now(timezone(timedelta(hours=3)))).total_seconds() / 60
        
        if queue_position and queue_position > 1:
            notification_text += f"<b>Статус:</b> Пост добавлен в очередь\n"
            notification_text += f"<b>Позиция в очереди:</b> #{queue_position}\n"
            notification_text += f"<b>Время публикации:</b> {scheduled_time_str}\n"
            if time_diff > 0:
                notification_text += f"<b>Ожидание:</b> {time_diff:.0f} минут\n"
            else:
                notification_text += f"<b>Публикация:</b> Моментально\n"
        else:
            if time_diff > 0:
                notification_text += f"<b>Статус:</b> Пост запланирован\n"
                notification_text += f"<b>Время публикации:</b> {scheduled_time_str}\n"
                notification_text += f"<b>Ожидание:</b> {time_diff:.0f} минут\n"
            else:
                notification_text += f"<b>Статус:</b> Пост будет опубликован моментально\n"
                notification_text += f"<b>Время публикации:</b> {scheduled_time_str}\n"
        
        notification_text += f"\n<b>Награда:</b> После публикации вы получите 50-500 токенов за пост (зависит от уровня)\n"
        notification_text += f"<b>Совет:</b> <blockquote>Используйте токены для покупки псевдонимов в /market</blockquote>\n\n"
        notification_text += f"<b>Следующий шаг:</b> Ожидайте уведомления о публикации"
        
        # Отправляем уведомление
        await bot.send_message(
            chat_id=user_id,
            text=notification_text,
            parse_mode="HTML"
        )
        logging.info(f"[send_approval_notification] Approval notification sent to user {user_id}")
        
    except Exception as e:
        logging.error(f"[send_approval_notification] Error sending approval notification: {e}")


async def send_publication_and_payment_notification(bot, user_id: int, post_content: str, tokens_added: int, new_balance: str, channel_message_id: int):
    """Отправляет объединенное уведомление о публикации и оплате"""
    try:
        # Формируем ссылку на пост в канале
        channel_id = os.getenv("ORACLE_CHANNEL_ID")
        if not channel_id:
            logging.error(f"[send_publication_and_payment_notification] CHANNEL_ID not set")
            return
            
        if channel_id.startswith('-100'):
            channel_id = channel_id[4:]  # Убираем префикс -100 для ссылки
        
        post_link = f"https://t.me/c/{channel_id}/{channel_message_id}"
        
        # Формируем объединенное сообщение
        notification_text = f"<b>Вопрос опубликован!</b>\n\n"
        notification_text += f"<b>Содержание:</b> «{post_content[:150]}{'...' if len(post_content) > 150 else ''}»\n\n"
        notification_text += f"<b>Ссылка:</b> <a href=\"{post_link}\">Открыть вопрос в канале</a>\n\n"
        notification_text += f"<b>Награда:</b> +{tokens_added} т. (баланс: {new_balance} т.)\n\n"
        notification_text += f"<b>Время:</b> {datetime.now(timezone(timedelta(hours=3))).strftime('%d.%m.%Y в %H:%M')}\n\n"
        notification_text += f"Используйте токены в /market для покупки псевдонимов"
        
        # Отправляем уведомление
        await bot.send_message(
            chat_id=user_id,
            text=notification_text,
            parse_mode="HTML",
            disable_web_page_preview=True
        )
        logging.info(f"[send_publication_and_payment_notification] Combined notification sent to user {user_id}")
        
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


def format_username(username):
    if not username or str(username).lower() == 'none':
        return 'N/A'
    return username


class SuggestStates(StatesGroup):
    waiting_for_confirm = State()


def register_suggest_handler(dp: Dispatcher):
    @dp.message()
    async def suggest_handler(message: types.Message, state: FSMContext):
        if message.from_user and message.from_user.first_name == "Telegram":
            comment_url = f"https://t.me/{BOT_NAME}?start={message.message_id}"

            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="💬 Ответить", url=comment_url)]
                ]
            )
            await message.reply(
                "<b>Теперь вы можете оставить анонимный ответ к этому вопросу:</b>",
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
        elif message.chat.type == 'private':
            content_type, post_content = get_content_type_and_text(message)
            user_id = message.from_user.id

            found_similar = False
            similar_link = None
            similar_content = None
            try:
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        "http://askmephi_search:8001/search/",
                        params={"question": post_content},
                        timeout=aiohttp.ClientTimeout(total=5)
                    ) as resp:
                        data = await resp.json()
                if data.get("found"):
                    found_similar = True
                    similar_link = data["link"]
                    similar_content = data.get("content")
            except Exception as e:
                logging.warning(f"[suggest_handler] tf-idf search error: {e}")
            
            if found_similar:
                preview = ""
                if isinstance(similar_content, str) and similar_content.strip():
                    words = similar_content.split()
                    preview = ' '.join(words[:15]) + ("..." if len(words) > 1 else "")
                text = (
                        "<b>Похожий анонимный вопрос уже был опубликован!</b>\n\n"
                    + (f"<blockquote>{preview}</blockquote>\n" if preview else "")
                    + f"<a href='{similar_link}'>Открыть в канале</a>\n\n"
                    + "<b>Ваш вопрос:</b>\n"
                    + f"<blockquote>{post_content}</blockquote>\n\n"
                    + "Все равно отправить этот вопрос в предложку?"
                    )
                keyboard = InlineKeyboardMarkup(
                        inline_keyboard=[
                            [InlineKeyboardButton(text="Отправить", callback_data=f"confirm_suggest_{user_id}")]
                        ]
                    )
                sent = await message.reply(text, reply_markup=keyboard, parse_mode="HTML")
                return
            else:
                text = (
                    f"Проверьте, всё ли верно:\n\n"
                    f"<code>{post_content}</code>\n\n"
                    f"Если всё правильно, нажмите 'Отправить'."
                )
                keyboard = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="Отправить", callback_data=f"confirm_suggest_{user_id}")]
                    ]
                )
                sent = await message.reply(text, reply_markup=keyboard, parse_mode="HTML")
                if sent and hasattr(sent, 'message_id'):
                    await state.update_data(confirm_msg_id=sent.message_id)
                await state.set_state(SuggestStates.waiting_for_confirm)
                return

    @dp.callback_query(F.data.startswith("confirm_suggest_"))
    async def confirm_suggest_callback(callback: types.CallbackQuery, state: FSMContext):
        msg_obj = callback.message
        if not msg_obj or not hasattr(msg_obj, 'reply_to_message') or not isinstance(msg_obj.reply_to_message, Message):
            logging.error('confirm_suggest_callback: reply_to_message is not a valid Message')
            await callback.answer("Ошибка: не найдено исходное сообщение пользователя")
            return
        original_msg = msg_obj.reply_to_message
        if not original_msg or not hasattr(original_msg, 'from_user') or not original_msg.from_user:
            await callback.answer("Ошибка: не удалось определить пользователя")
            return
        user_id = int(callback.data.replace("confirm_suggest_", ""))

        content_type, post_content = get_content_type_and_text(original_msg)
        offers_chat_id = os.getenv('ORACLE_OFFERS_CHAT_ID')
        if offers_chat_id is None:
            await callback.answer("Ошибка: не настроен offers_chat_id")
            return
        try:
            await callback.bot.delete_message(callback.message.chat.id, msg_obj.message_id)
        except Exception:
            pass
        if not hasattr(original_msg, 'message_id') or original_msg.message_id is None:
            await callback.answer("Ошибка: не удалось получить message_id пользователя")
            return
        msg = await callback.bot.copy_message(
            chat_id=offers_chat_id,
            from_chat_id=callback.message.chat.id if hasattr(callback.message, 'chat') and callback.message.chat else offers_chat_id,
            message_id=original_msg.message_id
        )
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{user_id}"),
                 InlineKeyboardButton(text="✅ Добавить", callback_data=f"approve_{user_id}"),
                 InlineKeyboardButton(text="# Тегнуть", callback_data=f"tag_{user_id}")
                 ]
            ]
        )
        author_info = await get_user_info(user_id)
        author_username = author_info.get('username', 'N/A')
        author_firstname = author_info.get('firstname', '')
        author_lastname = author_info.get('lastname', '')
        author_level = author_info.get('level', 'N/A')
        author_balance = author_info.get('balance', 'N/A')
        admin_message = (
            f"#незапостчено\n"
            f"<b>Новый вопрос в предложке</b>\n\n"
            f"<b>Автор:</b> <code>{user_id}</code> @{author_username}\n"
            f"<b>Имя:</b> {author_firstname} {author_lastname}\n"
            f"<b>Уровень:</b> {author_level}\n"
            f"<b>Баланс:</b> {author_balance} т.\n"
            f"<b>Тип контента:</b> {content_type}\n"
            f"<b>Время:</b> {datetime.now(timezone(timedelta(hours=3))).strftime('%d.%m.%Y в %H:%M')}\n\n"
            f"<b>Содержание:</b> {post_content[:300]}{'...' if post_content and len(post_content) > 300 else ''}"
        )
        if not hasattr(msg_obj, 'bot') or msg_obj.bot is None:
            logging.error('message.bot is None')
            return
        await msg_obj.bot.send_message(
            chat_id=offers_chat_id,
            text=admin_message,
            reply_to_message_id=msg.message_id if msg and hasattr(msg, 'message_id') else None,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
        await send_submission_notification(msg_obj.bot, user_id, post_content)
        await callback.answer("Вопрос отправлен!")
        await state.clear()

    @dp.callback_query(F.data.startswith(("tag_",)))
    async def tag_callback(callback: types.CallbackQuery):
        user_id = int(callback.data.replace("tag_", ""))
       
        ask_hashtags = os.getenv("ASK_HASHTAGS", "")
        tags = [tag.strip() for tag in ask_hashtags.split(";") if tag.strip()]

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
              [InlineKeyboardButton(text=tag, callback_data=f"settag_{tag}_{user_id}")]
            for tag in tags
            ]
        )       
        await callback.message.edit_reply_markup(reply_markup=keyboard)
    @dp.callback_query(F.data.startswith(("settag_",)))
    async def settag_callback(callback: types.CallbackQuery):
        old_text = callback.message.reply_to_message.text
        user_id = int(callback.data.split("_")[2])
        tag =  (callback.data.split("_")[1])
        await callback.message.reply_to_message.edit_text(text=f"<i>#{tag}</i>\n\n{old_text}", parse_mode=ParseMode.HTML)
        
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{user_id}"),
                 InlineKeyboardButton(text="✅ Добавить", callback_data=f"approve_{user_id}"),
                 ]
            ]
        )
        
        await callback.message.edit_reply_markup(reply_markup=keyboard)
    @dp.callback_query(F.data.startswith(("reject_",)))
    async def reject_callback(callback: types.CallbackQuery):
        # Парсим user_id и telegram_id из callback_data
        user_id = int(callback.data.replace("reject_", ""))
       
        telegram_id = int(callback.message.reply_to_message.message_id)
        # Получаем пост из БД
        try:
            post_info = await get_post_by_telegram_id(telegram_id)

            content_type = post_info.get('media_type', 'text')
            post_content = post_info.get('content', '')
        except:
            post_content = callback.message.reply_to_message.text
            content_type = "None" 
        # Получаем подробную инфу об авторе
        author_info = await get_user_info(user_id)
        author_username = author_info.get('username', 'N/A')
        author_firstname = author_info.get('firstname', '')
        author_lastname = author_info.get('lastname', '')
        author_level = author_info.get('level', 'N/A')
        author_balance = author_info.get('balance', 'N/A')
        # Отклоняем пост
        result = await mark_post_as_rejected_by_telegram_id(telegram_id)
        logging.info(f"[reject_callback] Post removed from queue: {result}")
        # Формируем сообщение об отклонении для админ чата
        admin_message_text = f"❌ <b>Вопрос отклонен!</b>\n\n"
        admin_message_text += f"<b>Автор:</b> <code>{user_id}</code> @{author_username}\n"
        admin_message_text += f"<b>Имя:</b> {author_firstname} {author_lastname}\n"
        admin_message_text += f"<b>Уровень:</b> {author_level}\n"
        admin_message_text += f"<b>Баланс:</b> {author_balance} т.\n"
        admin_message_text += f"📝 <b>Содержание:</b> {post_content[:100]}{'...' if len(post_content) > 100 else ''}\n"
        admin_message_text += f"📄 <b>Тип контента:</b> {content_type}\n\n"
        admin_message_text += f"⏰ <b>Время отклонения:</b> {datetime.now(timezone(timedelta(hours=3))).strftime('%d.%m.%Y в %H:%M')}\n"
        admin_message_text += f"👮 <b>Админ:</b> {callback.from_user.username or callback.from_user.first_name}"
        await callback.message.edit_text(
            text=admin_message_text,
            parse_mode="HTML"
        )
        await callback.answer("Вопрос отклонён!")
        await send_rejection_notification(callback.bot, user_id, post_content)

    @dp.callback_query(F.data.startswith(("approve_",)))
    async def approve_callback(callback: types.CallbackQuery):
        # Парсим user_id и telegram_id из callback_data
        
        _, user_id = callback.data.split("_")
        user_id = int(user_id)
        telegram_id = callback.message.reply_to_message.message_id
        # Получаем оригинальное сообщение пользователя через reply_to_message
        msg_obj = callback.message
        if not msg_obj or not hasattr(msg_obj, 'reply_to_message') or not isinstance(msg_obj.reply_to_message, Message):
            logging.error('approve_callback: reply_to_message is not a valid Message')
            await callback.answer('Ошибка: не найдено исходное сообщение пользователя')
            return
        original_msg = msg_obj.reply_to_message
        if not original_msg or not hasattr(original_msg, 'from_user') or not original_msg.from_user:
            await callback.answer("Ошибка: не удалось определить пользователя")
            return
        # Извлекаем данные из сообщения
        content_type, post_content = get_content_type_and_text(original_msg)
        # Проверяем, есть ли уже пост с таким telegram_id
       
            # Если нет — создаём пост
        moscow_tz = pytz.timezone('Europe/Moscow')
        now = datetime.now(timezone(timedelta(hours=3)))
            # Получаем автора
        author_info = await get_user_info(user_id)
        username = author_info.get('username', None)
        firstname = author_info.get('firstname', None)
        lastname = author_info.get('lastname', None)
        await try_create_user(
                user_id=user_id,
                username=username,
                firstname=firstname,
                lastname=lastname
            )
            # Время публикации рассчитываем как раньше
        active_posts_count = await get_active_posts_count()
        if active_posts_count > 0:
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
            scheduled_time = last_post_dt + timedelta(minutes=POST_INTERVAL_MINUTES)
        else:
            last_published_data = await get_last_published_post_time()
            if 'error' in last_published_data:
                scheduled_time = now
            else:
                last_post_time_str = last_published_data.get('channel_posted_at')
                try:
                    if last_post_time_str and ('+' in last_post_time_str or 'Z' in last_post_time_str):
                        last_post_dt = datetime.strptime(last_post_time_str.replace('Z', '+0000'), "%Y-%m-%dT%H:%M:%S%z")
                        last_post_dt = last_post_dt.astimezone(moscow_tz)
                    else:
                        last_post_dt = moscow_tz.localize(datetime.strptime(last_post_time_str, "%Y-%m-%d %H:%M:%S"))
                    time_since_last_post = (now - last_post_dt).total_seconds() / 60
                    if time_since_last_post >= POST_INTERVAL_MINUTES:
                        scheduled_time = now
                    else:
                        remaining_minutes = POST_INTERVAL_MINUTES - time_since_last_post
                        scheduled_time = now + timedelta(minutes=remaining_minutes)
                except ValueError as e:
                    scheduled_time = now
        scheduled_hour = scheduled_time.hour
        if 1 <= scheduled_hour < 10:
            scheduled_time = scheduled_time.replace(hour=10, minute=0, second=0, microsecond=0)
            logging.info(f"[approve_callback] Post scheduled time moved to 10:00 due to inactive hours (was {scheduled_hour}:{scheduled_time.minute})")
        # Создаём пост
        create_result = await try_create_post(author_id=user_id, content=post_content, telegram_id=telegram_id, post_time=scheduled_time)
        if 'error' in create_result:
            await callback.answer("Ошибка создания поста!")
            return
        post_info = await get_post_by_telegram_id(telegram_id)
        if 'error' in post_info or not post_info.get('id'):
            await callback.answer("Ошибка: не удалось получить пост после создания!")
            return
    # ... остальная логика approve_callback без изменений, используя post_info ...

        # Проверяем, не попадает ли время в неактивный период (01:00-10:00)
        scheduled_hour = scheduled_time.hour
        if 1 <= scheduled_hour < 10:
            # Переносим время на 10:00 того же дня
            scheduled_time = scheduled_time.replace(hour=10, minute=0, second=0, microsecond=0)
            logging.info(f"[approve_callback] Post scheduled time moved to 10:00 due to inactive hours (was {scheduled_hour}:{scheduled_time.minute})")

        # Создаём пост через API
        # Удаляю вызов:
        # create_result = await try_create_post(author_id=user_id, content=post_content, telegram_id=telegram_id, post_time=scheduled_time)
        # if 'error' in create_result:
        #     await callback.answer("Ошибка создания поста!")
        #     return

        # Получаем post_info по telegram_id
        post_info = await get_post_by_telegram_id(telegram_id)
        if 'error' in post_info or not post_info.get('id'):
            await callback.answer("Ошибка: не удалось получить пост после создания!")
            return

        # Проверяем, пора ли публиковать пост
        now_utc = datetime.utcnow().replace(tzinfo=timezone.utc)
        post_time_utc = post_info.get('posted_at')
        if post_time_utc:
            try:
                if '+' in post_time_utc or 'Z' in post_time_utc:
                    post_time_dt = datetime.strptime(post_time_utc.replace('Z', '+0000'), "%Y-%m-%dT%H:%M:%S%z")
                else:
                    post_time_dt = datetime.strptime(post_time_utc, "%Y-%m-%d %H:%M:%S")
                    post_time_dt = post_time_dt.replace(tzinfo=timezone.utc)
            except Exception:
                post_time_dt = now_utc
        else:
            post_time_dt = now_utc

        if now_utc >= post_time_dt:
            # Время публикации пришло — публикуем и оплачиваем
            publish_result = await publish_post_now(post_info['id'])
            if 'error' in publish_result:
                await callback.message.answer(f"❌ Ошибка публикации: {publish_result['error']}")
                return
            tokens_added = publish_result.get('tokens_added', 0)
            author_level = publish_result.get('author_level', 1)
            # Публикуем в канал
            success, channel_message_id = await publish_to_channel(post_info, callback.bot)
            if not success:
                await callback.message.answer("❌ Ошибка публикации в канал")
                return
            await update_post_channel_info(post_info['id'], channel_message_id)
            await recalculate_queue_after_immediate_publication()
            # Уведомление пользователю
            await send_publication_and_payment_notification(callback.bot, user_id, post_info.get('content', ''), tokens_added, publish_result.get('author_balance', 'N/A'), channel_message_id)
            # Получаем подробную инфу об авторе
            author_info = await get_user_info(user_id)
            author_username = author_info.get('username', 'N/A')
            author_firstname = author_info.get('firstname', '')
            author_lastname = author_info.get('lastname', '')
            author_level = author_info.get('level', 'N/A')
            author_balance = author_info.get('balance', 'N/A')
            # Сообщение для админов
            admin_message_text = f"🚀 <b>Вопрос опубликован!</b>\n\n"
            admin_message_text += f"<b>Автор:</b> <code>{user_id}</code> @{author_username}\n"
            admin_message_text += f"<b>Имя:</b> {author_firstname} {author_lastname}\n"
            admin_message_text += f"<b>Уровень:</b> {author_level}\n"
            admin_message_text += f"<b>Баланс:</b> {author_balance} т.\n"
            admin_message_text += f"<b>Содержание:</b> {post_info.get('content', '')[:100]}{'...' if len(post_info.get('content', '')) > 100 else ''}\n\n"
            admin_message_text += f"<b>Оплата:</b>\n"
            admin_message_text += f"<b>Уровень автора:</b> {author_level}\n"
            admin_message_text += f"<b>Токенов выплачено:</b> {tokens_added}\n"
            admin_message_text += f"<b>Новый баланс автора:</b> {publish_result.get('author_balance', 'N/A')} т.\n\n"
            admin_message_text += f"<b>ID поста:</b> {post_info['id']}\n"
            admin_message_text += f"<b>Время публикации:</b> {datetime.now(timezone(timedelta(hours=3))).strftime('%d.%m.%Y в %H:%M')}\n"
            admin_message_text += f"<b>Админ:</b> {callback.from_user.username or callback.from_user.first_name}"
            admin_message_text = re.sub(r"#незапостчено", "#запостчено", admin_message_text)
            await callback.message.edit_text(text=admin_message_text, parse_mode="HTML")
        else:
            # Время публикации ещё не пришло — ставим в очередь
            scheduled_time_str = scheduled_time.strftime("%d.%m.%Y в %H:%M")
            queue_position = active_posts_count + 1 if active_posts_count > 0 else 1
            await send_approval_notification(callback.bot, user_id, post_content, scheduled_time, queue_position)
            # Получаем подробную инфу об авторе
            author_info = await get_user_info(user_id)
            author_username = author_info.get('username', 'N/A')
            author_firstname = author_info.get('firstname', '')
            author_lastname = author_info.get('lastname', '')
            author_level = author_info.get('level', 'N/A')
            author_balance = author_info.get('balance', 'N/A')
            # Создаём кнопки для управления постом только если есть post_info['id']
            if post_info.get('id'):
                keyboard = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="Отклонить", callback_data=f"reject_{user_id}")],
                        [InlineKeyboardButton(text="Опубликовать сейчас", callback_data=f"publish_now_{user_id}_{post_info.get('id')}")]
                    ]
                )
            else:
                keyboard = None
            admin_message_text = f"#незапостчено\n🕒 <b>Вопрос поставлен в очередь</b>\n\n"
            admin_message_text += f"<b>Автор:</b> <code>{user_id}</code> @{author_username}\n"
            admin_message_text += f"<b>Имя:</b> {author_firstname} {author_lastname}\n"
            admin_message_text += f"<b>Уровень:</b> {author_level}\n"
            admin_message_text += f"<b>Баланс:</b> {author_balance} т.\n"
            admin_message_text += f"<b>Содержание:</b> {post_content[:100]}{'...' if len(post_content) > 100 else ''}\n\n"
            admin_message_text += f"<b>Статус:</b> В очереди\n"
            admin_message_text += f"<b>Позиция в очереди:</b> {queue_position}\n"
            admin_message_text += f"<b>Время публикации:</b> {scheduled_time_str}\n"
            admin_message_text += f"<b>ID поста:</b> {post_info.get('id', 'N/A')}\n"
            admin_message_text += f"<b>Админ:</b> {callback.from_user.username or callback.from_user.first_name}"
            admin_message_text = re.sub(r"#незапостчено", "#запостчено", admin_message_text)
            await callback.message.edit_text(text=admin_message_text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer("Пост обработан")

    @dp.callback_query(F.data.startswith(("publish_now_",)))
    async def publish_now_callback(callback: types.CallbackQuery):
        """Обработчик кнопки 'Опубликовать сейчас' - немедленно публикует пост и оплачивает его"""
        # Получаем post_id из callback_data
        try:
            user_id = int(callback.data.split("_")[2])
            post_id = int(callback.data.split("_")[3])
        except Exception:
            await callback.answer('Ошибка: не удалось определить ID поста')
            return
        # Получаем информацию о посте по post_id
       
        telegram_id = callback.message.reply_to_message.message_id
        # Сразу отвечаем на callback, чтобы избежать timeout
      
        await callback.answer("🚀 Публикуем пост...")
        try:
            logging.info(f"[publish_now_callback] Processing immediate publication for user_id={user_id}, telegram_id={telegram_id}")
            # Проверяем, что пост еще не опубликован
            # Немедленно публикуем пост и обрабатываем оплату
            publish_result = await publish_post_now(post_id)
            if 'error' in publish_result:
                logging.error(f"[publish_now_callback] Publication failed: {publish_result['error']}")
                await callback.message.answer(f"❌ Ошибка публикации: {publish_result['error']}")
                return
            logging.info(f"[publish_now_callback] Publication successful: {publish_result}")
            # Получаем информацию о выплаченных токенах
            tokens_added = publish_result.get('tokens_added', 0)
            author_level = publish_result.get('author_level', 1)
            # Публикуем в канал
            success, channel_message_id = await publish_to_channel(telegram_id, callback.bot)
            if not success:
                await callback.message.answer("❌ Ошибка публикации в канал")
                return
            # Обновляем информацию о канале
            await update_post_channel_info(post_id, channel_message_id)
            # Пересчитываем очередь после моментальной публикации
            queue_recalc_result = await recalculate_queue_after_immediate_publication()
            post_info = await get_post_by_telegram_id(telegram_id)
            if 'error' in queue_recalc_result:
                logging.warning(f"[publish_now_callback] Queue recalculation failed: {queue_recalc_result['error']}")
            else:
                logging.info(f"[publish_now_callback] Queue recalculated: {queue_recalc_result.get('message', 'Success')}")
            logging.info(f"[publish_now_callback] Successfully published and paid post {post_id}: level {author_level}, {tokens_added} tokens")
            # Отправляем объединенное уведомление о публикации и оплате
            await send_publication_and_payment_notification(callback.bot, user_id, post_info.get('content', ''), tokens_added, publish_result.get('author_balance', 'N/A'), channel_message_id)
            # Убираем кнопки и показываем результат
            await callback.message.delete_reply_markup()
            # Получаем подробную инфу об авторе
            author_info = await get_user_info(user_id)
            author_username = author_info.get('username', 'N/A')
            author_firstname = author_info.get('firstname', '')
            author_lastname = author_info.get('lastname', '')
            author_level = author_info.get('level', 'N/A')
            author_balance = author_info.get('balance', 'N/A')
            # Сообщение для админов
            admin_message_text = f"🚀 <b>Вопрос опубликован и оплачен</b>\n\n"
            admin_message_text += f"<b>Автор:</b> <code>{user_id}</code> @{author_username}\n"
            admin_message_text += f"<b>Имя:</b> {author_firstname} {author_lastname}\n"
            admin_message_text += f"<b>Уровень:</b> {author_level}\n"
            admin_message_text += f"<b>Баланс:</b> {author_balance} т.\n"
            admin_message_text += f"<b>Содержание:</b> {post_info.get('content', '')[:100]}{'...' if len(post_info.get('content', '')) > 100 else ''}\n\n"
            admin_message_text += f"<b>Оплата:</b>\n"
            admin_message_text += f"<b>Уровень автора:</b> {author_level}\n"
            admin_message_text += f"<b>Токенов выплачено:</b> {tokens_added}\n"
            admin_message_text += f"<b>Новый баланс автора:</b> {publish_result.get('author_balance', 'N/A')} т.\n\n"
            admin_message_text += f"<b>ID поста:</b> {post_info['id']}\n"
            admin_message_text += f"<b>Время публикации:</b> {datetime.now(timezone(timedelta(hours=3))).strftime('%d.%m.%Y в %H:%M')}\n"
            admin_message_text += f"<b>Админ:</b> {callback.from_user.username or callback.from_user.first_name}"
            admin_message_text = re.sub(r"#незапостчено", "#запостчено", admin_message_text)
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
        if not callback.message or not hasattr(callback.message, 'reply_to_message') or callback.message.reply_to_message is None:
            logging.error('pay_callback: reply_to_message is None')
            await callback.answer('Ошибка: не найдено исходное сообщение пользователя')
            return
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
                error_text = author_info.get('error', '')
                if '404' in error_text:
                    await callback.answer(f'❌ Пользователь с ID {author_id} не существует')
                else:
                    await callback.answer(f'❌ Ошибка: не удалось получить информацию об авторе')
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
            
            # Получаем подробную инфу об авторе
            author_info = await get_user_info(user_id)
            author_username = author_info.get('username', 'N/A')
            author_firstname = author_info.get('firstname', '')
            author_lastname = author_info.get('lastname', '')
            author_level = author_info.get('level', 'N/A')
            author_balance = author_info.get('balance', 'N/A')
            # Формируем сообщение об оплате для админ чата
            admin_message_text = f"<b>Вопрос оплачен</b>\n\n"
            admin_message_text += f"<b>Автор:</b> {author_id}\n"
            admin_message_text += f"<b>Содержание:</b> {post_info.get('content', '')[:100]}{'...' if len(post_info.get('content', '')) > 100 else ''}\n\n"
            admin_message_text += f"<b>Оплата:</b>\n"
            admin_message_text += f"<b>Уровень автора:</b> {author_level}\n"
            admin_message_text += f"<b>Токенов выплачено:</b> {tokens_added}\n"
            admin_message_text += f"<b>Новый баланс автора:</b> {payment_result.get('author_balance', 'N/A')} т.\n\n"
            admin_message_text += f"<b>ID поста:</b> {post_info['id']}\n"
            admin_message_text += f"<b>Время выплаты:</b> {datetime.now(timezone(timedelta(hours=3))).strftime('%d.%m.%Y в %H:%M')}\n"
            admin_message_text += f"<b>Админ:</b> {callback.from_user.username or callback.from_user.first_name}"
            admin_message_text = re.sub(r"#незапостчено", "#запостчено", admin_message_text)
            
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

# --- Новый минималистичный обработчик предложки ---
from aiogram import Router
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.enums import ParseMode
from aiogram.filters import Command
import os
from db.wapi import try_create_post, mark_post_as_rejected_by_telegram_id, get_user_info, get_post_by_telegram_id
from datetime import datetime, timedelta, timezone

suggest_router = Router()

ADMIN_CHAT_ID = os.getenv('ORACLE_OFFERS_CHAT_ID')

# Пользователь отправляет пост в личку боту
@suggest_router.message()
async def handle_suggest_message(message: Message):
    if message.chat.type != 'private' or not ADMIN_CHAT_ID:
        return
    user_id = message.from_user.id
    # Пересылаем сообщение в админчат
    fwd = await message.forward(ADMIN_CHAT_ID)
    # Получаем инфу о пользователе
    user_info = await get_user_info(user_id)
    username = user_info.get('username', 'N/A')
    level = user_info.get('level', 'N/A')
    balance = user_info.get('balance', 'N/A')
    # Формируем сообщение для админов
    admin_text = (
        f"<b>Пост в предложке</b>\n"
        f"<b>Автор:</b> <code>{user_id}</code> @{username}\n"
        f"<b>Уровень:</b> {level}\n"
        f"<b>Баланс:</b> {balance} т.\n"
        f"<b>Время:</b> {datetime.now(timezone(timedelta(hours=3))).strftime('%d.%m.%Y в %H:%M')}\n"
    )
    # Кнопки с user_id и message_id
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Добавить", callback_data=f"approve_simple_{user_id}_{fwd.message_id}"),
                InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_simple_{user_id}_{fwd.message_id}")
            ]
        ]
    )
    await message.bot.send_message(
        chat_id=ADMIN_CHAT_ID,
        text=admin_text,
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML,
        reply_to_message_id=fwd.message_id
    )
    await message.reply("Пост отправлен на рассмотрение!", parse_mode=ParseMode.HTML)

# Кнопка "Добавить в очередь"
@suggest_router.callback_query(lambda c: c.data.startswith("approve_simple_"))
async def handle_approve_simple(callback: CallbackQuery):
    _, user_id, telegram_id = callback.data.split("_")[-3:]
    user_id = int(user_id)
    telegram_id = int(telegram_id)
    # Получаем текст поста через get_post_by_telegram_id (или можно через callback.message.reply_to_message)
    post_info = await get_post_by_telegram_id(telegram_id)
    if post_info and not post_info.get('id'):
        # Если поста нет — создаём
        now = datetime.now(timezone(timedelta(hours=3)))
        content = callback.message.reply_to_message.text if callback.message.reply_to_message else '[NO TEXT]'
        await try_create_post(author_id=user_id, content=content, post_time=now, telegram_id=telegram_id)
    await callback.answer("Пост добавлен в очередь!")
    await callback.message.edit_text("✅ Пост добавлен в очередь", parse_mode=ParseMode.HTML)

# Кнопка "Отклонить"
@suggest_router.callback_query(lambda c: c.data.startswith("reject_simple_"))
async def handle_reject_simple(callback: CallbackQuery):
    _, user_id, telegram_id = callback.data.split("_")[-3:]
    telegram_id = int(telegram_id)
    await mark_post_as_rejected_by_telegram_id(telegram_id)
    await callback.answer("Пост отклонён!")
    await callback.message.edit_text("❌ Пост отклонён", parse_mode=ParseMode.HTML)

# --- Конец нового обработчика ---