from aiogram import types, F, Dispatcher
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode, ContentType
from datetime import datetime, timedelta, timezone
import os
import pytz
from datetime import time
from db.wapi import get_last_post, try_create_post, mark_post_as_posted, mark_post_as_rejected_by_telegram_id, get_post_by_telegram_id, process_post_payment, get_user_info, get_active_posts_count, publish_post_now, get_last_published_post_time, recalculate_queue_after_immediate_publication, try_create_user
from SugQueue import publish_to_channel, update_post_channel_info, send_publication_notification
import logging
import re
import aiohttp
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message


ACTIVE_START_HOUR = 10  # 10:00
ACTIVE_END_HOUR = 1     # 01:00 следующего дня
POST_INTERVAL_MINUTES = 30
BOT_NAME = os.getenv("ORACLE_BOT_NAME")

async def send_submission_notification(bot, user_id: int, post_content: str):
    """Отправляет уведомление пользователю о том, что пост отправлен на рассмотрение"""
    try:
        notification_text = (
            "✉️ <b>Анонимный вопрос отправлен на модерацию</b>\n\n"
            "<b>Содержание:</b>\n"
            f"<code>{post_content[:300]}{'...' if len(post_content) > 300 else ''}</code>\n\n"
            f"<b>Время:</b> {datetime.now(timezone(timedelta(hours=3))).strftime('%d.%m.%Y в %H:%M')}\n\n"
            "<b>Процесс модерации:</b>\n"
            "<blockquote>• Администрация проверит контент\n"
            "• Уведомление о решении\n"
            "• Публикация при одобрении</blockquote>\n\n"
            "📬 <i>Пока ожидаете: изучите /help и /market</i>"
        )
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
        notification_text = (
            "❌ <b>Ваш анонимный вопрос не прошёл модерацию</b>\n\n"
            "<b>Содержание:</b>\n"
            f"<code>{post_content[:300]}{'...' if len(post_content) > 300 else ''}</code>\n\n"
            "<b>Возможные причины:</b>\n"
            "<blockquote>• Вопрос не соответствует правилам сообщества\n"
            "• Содержание не подходит для канала\n"
            "• Дублирование существующего контента</blockquote>\n\n"
            "<b>Что делать:</b>\n"
            "<blockquote>• Пересмотрите содержание вопроса\n"
            "• Убедитесь, что вопрос соответствует тематике\n"
            "• Попробуйте отправить новый анонимный вопрос</blockquote>\n\n"
            "<b>Полезные команды:</b>\n"
            "• /help — получить справку\n"
            "• /market — купить псевдонимы\n\n"
            f"<b>Время отклонения:</b> {datetime.now(timezone(timedelta(hours=3))).strftime('%d.%m.%Y в %H:%M')}"
        )
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
        scheduled_time_str = scheduled_time.strftime("%d.%m.%Y в %H:%M")
        time_diff = (scheduled_time - datetime.now(timezone(timedelta(hours=3)))).total_seconds() / 60
        notification_text = (
            "✅ <b>Ваш анонимный вопрос одобрен</b>\n\n"
            "<b>Содержание:</b>\n"
            f"<code>{post_content[:300]}{'...' if len(post_content) > 300 else ''}</code>\n\n"
        )
        if queue_position and queue_position > 1:
            notification_text += (
                f"<b>Статус:</b> <i>Анонимный вопрос добавлен в очередь</i>\n"
                f"<b>Позиция в очереди:</b> <b>#{queue_position}</b>\n"
                f"<b>Время публикации:</b> {scheduled_time_str}\n"
                + (f"<b>Ожидание:</b> <i>{time_diff:.0f} минут</i>\n" if time_diff > 0 else "<b>Публикация:</b> <i>Моментально</i>\n")
            )
        else:
            if time_diff > 0:
                notification_text += (
                    f"<b>Статус:</b> <i>Анонимный вопрос запланирован</i>\n"
                    f"<b>Время публикации:</b> {scheduled_time_str}\n"
                    f"<b>Ожидание:</b> <i>{time_diff:.0f} минут</i>\n"
                )
            else:
                notification_text += (
                    f"<b>Статус:</b> <i>Анонимный вопрос будет опубликован моментально</i>\n"
                    f"<b>Время публикации:</b> {scheduled_time_str}\n"
                )
        notification_text += (
            "\n💰 <b>Награда:</b> После публикации вы получите <b>50-500 токенов</b> за анонимный вопрос (зависит от уровня)\n"
            "<b>Совет:</b> <blockquote>Используйте токены для покупки псевдонимов в /market</blockquote>\n\n"
            "<b>Следующий шаг:</b> Ожидайте уведомления о публикации"
        )
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
        channel_id = os.getenv("CHANNEL_ID")
        if not channel_id:
            logging.error(f"[send_publication_and_payment_notification] CHANNEL_ID not set")
            return
        if channel_id.startswith('-100'):
            channel_id = channel_id[4:]
        post_link = f"https://t.me/c/{channel_id}/{channel_message_id}"
        notification_text = (
            "🚀 <b>Анонимный вопрос опубликован и оплачен</b>\n\n"
            "<b>Содержание:</b>\n"
            f"<code>{post_content[:300]}{'...' if len(post_content) > 300 else ''}</code>\n\n"
            f"<b>Ссылка:</b> <a href=\"{post_link}\">Открыть вопрос в канале</a>\n\n"
            f"💰 <b>Награда:</b> <b>+{tokens_added} т.</b> (баланс: <b>{new_balance} т.</b>)\n\n"
            f"<b>Время:</b> {datetime.now(timezone(timedelta(hours=3))).strftime('%d.%m.%Y в %H:%M')}\n\n"
            "<i>Используйте токены в /market для покупки псевдонимов</i>"
        )
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
                    [InlineKeyboardButton(text="💬 Комментировать", url=comment_url)]
                ]
            )
            await message.reply(
                "<b>Теперь вы можете оставить анонимный комментарий к этому вопросу:</b>",
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
            return

        if message.chat.type == 'private':
            content_type, post_content = get_content_type_and_text(message)
            user_id = message.from_user.id
            # Поиск похожего вопроса через микросервис
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
                    preview = ' '.join(words[:15]) + ("..." if len(words) > 15 else "")
                text = (
                    "<b>Похожий анонимный вопрос уже был опубликован!</b>\n\n"
                    + (f"<blockquote>{preview}</blockquote>\n" if preview else "")
                    + f"<a href='{similar_link}'>Открыть в канале</a>\n\n"
                    + "<b>Ваш вопрос:</b>\n"
                    + f"<blockquote>{post_content}</blockquote>\n\n"
                    + "Все равно отправить этот вопрос в предложку?"
                )
            else:
                text = (
                    f"Проверьте, всё ли верно:\n\n"
                    f"<blockquote>{post_content}</blockquote>\n\n"
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
        user_id = original_msg.from_user.id
        content_type, post_content = get_content_type_and_text(original_msg)
        offers_chat_id = os.getenv('ORACLE_OFFERS_CHAT_ID')
        if offers_chat_id is None:
            await callback.answer("Ошибка: не настроен offers_chat_id")
            return

        # Удаляем сообщение с кнопкой подтверждения
        try:
            await callback.bot.delete_message(callback.message.chat.id, msg_obj.message_id)
        except Exception:
            pass

        # 1. Копируем сообщение пользователя в offers_chat_id
        if not hasattr(original_msg, 'message_id') or original_msg.message_id is None:
            await callback.answer("Ошибка: не удалось получить message_id пользователя")
            return
        msg = await callback.bot.copy_message(
            chat_id=offers_chat_id,
            from_chat_id=callback.message.chat.id if hasattr(callback.message, 'chat') and callback.message.chat else offers_chat_id,
            message_id=original_msg.message_id
        )

        # 2. Формируем admin_message
        author_info = await get_user_info(user_id)
        author_username = author_info.get('username', 'N/A')
        author_firstname = author_info.get('firstname', '')
        author_lastname = author_info.get('lastname', '')
        author_level = author_info.get('level', 'N/A')
        author_balance = author_info.get('balance', 'N/A')
        admin_message = (
            f"#незапостчено\n"
            f"<b>Новый анонимный вопрос в предложке</b>\n\n"
            f"<b>Автор:</b> <code>{user_id}</code> @{author_username}\n"
            f"<b>Имя:</b> {author_firstname} {author_lastname}\n"
            f"<b>Уровень:</b> {author_level}\n"
            f"<b>Баланс:</b> {author_balance} т.\n"
            f"<b>Тип контента:</b> {content_type}\n"
            f"<b>Время:</b> {datetime.now(timezone(timedelta(hours=3))).strftime('%d.%m.%Y в %H:%M')}\n\n"
            f"<b>Содержание:</b> {post_content[:300]}{'...' if post_content and len(post_content) > 300 else ''}"
        )
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{original_msg.message_id}"),
                 InlineKeyboardButton(text="✅ Добавить", callback_data=f"approve_{original_msg.message_id}")]
            ]
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

        # 3. Уведомление пользователю
        await send_submission_notification(msg_obj.bot, user_id, post_content)
        await callback.answer("Вопрос отправлен!")
        await state.clear()

    @dp.callback_query(F.data.startswith(("reject_",)))
    async def reject_callback(callback: types.CallbackQuery):
        try:
            telegram_id = int(callback.data.split("_")[1])
        except (IndexError, ValueError, AttributeError):
            await callback.answer("Ошибка: не удалось определить id вопроса")
            return
        post_info = await get_post_by_telegram_id(telegram_id)
        if not post_info or 'error' in post_info:
            logging.info(f"[reject_callback] Post not in queue, just rejecting")
            user_id = 'N/A'
            post_content = ''
            content_type = 'text'
        else:
            result = await mark_post_as_rejected_by_telegram_id(telegram_id)
            logging.info(f"[reject_callback] Post removed from queue: {result}")
            user_id = post_info.get('author', 'N/A')
            post_content = post_info.get('content', '')
            content_type = post_info.get('media_type', 'text')
        author_info = await get_user_info(user_id) if user_id != 'N/A' else {}
        author_username = author_info.get('username', 'N/A')
        author_firstname = author_info.get('firstname', '')
        author_lastname = author_info.get('lastname', '')
        author_level = author_info.get('level', 'N/A')
        author_balance = author_info.get('balance', 'N/A')
        admin_message_text = f"❌ <b>Анонимный вопрос не прошёл модерацию!</b>\n\n"
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
        if user_id != 'N/A':
            await send_rejection_notification(callback.bot, user_id, post_content)

    @dp.callback_query(F.data.startswith(("approve_",)))
    async def approve_callback(callback: types.CallbackQuery):
        msg_obj = callback.message
        if not msg_obj or not hasattr(msg_obj, 'reply_to_message') or not isinstance(msg_obj.reply_to_message, Message):
            logging.error('approve_callback: reply_to_message is not a valid Message')
            await callback.answer('Ошибка: не найдено исходное сообщение пользователя')
            return
        original_msg = msg_obj.reply_to_message
        if not original_msg or not hasattr(original_msg, 'from_user') or not original_msg.from_user:
            await callback.answer("Ошибка: не удалось определить пользователя")
            return
        user_id = original_msg.from_user.id
        content_type, post_content = get_content_type_and_text(original_msg)
        # Гарантируем, что пользователь есть в базе
        await try_create_user(
            user_id=user_id,
            username=original_msg.from_user.username,
            firstname=original_msg.from_user.first_name,
            lastname=original_msg.from_user.last_name
        )
        moscow_tz = pytz.timezone('Europe/Moscow')
        now = datetime.now(timezone(timedelta(hours=3)))

        # Проверяем количество активных постов в очереди
        active_posts_count = await get_active_posts_count()
        logging.info(f"[approve_callback] Active posts in queue: {active_posts_count}")

        # Если есть очередь, рассчитываем время относительно последнего поста в очереди
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

        # Проверяем, не попадает ли время в неактивный период (01:00-10:00)
        scheduled_hour = scheduled_time.hour
        if 1 <= scheduled_hour < 10:
            # Переносим время на 10:00 того же дня
            scheduled_time = scheduled_time.replace(hour=10, minute=0, second=0, microsecond=0)
            logging.info(f"[approve_callback] Post scheduled time moved to 10:00 due to inactive hours (was {scheduled_hour}:{scheduled_time.minute})")

        # Получаем тип контента и текст для БД
        content_type, post_content = get_content_type_and_text(original_msg)
        if not post_content:
            await callback.answer("Ошибка: контент вопроса пустой!")
            return

        # Логируем payload для try_create_post
        logging.info(f"[approve_callback] try_create_post payload: author_id={user_id}, content={post_content[:100]}, telegram_id={original_msg.message_id}, post_time={scheduled_time}")

        # Создаём пост через API
        create_result = await try_create_post(author_id=user_id, content=post_content, telegram_id=original_msg.message_id, post_time=scheduled_time)
        logging.info(f"[approve_callback] try_create_post result: {create_result}")
        if 'error' in create_result:
            await callback.answer("Ошибка создания вопроса!")
            return

        # Получаем post_info по telegram_id
        post_info = await get_post_by_telegram_id(original_msg.message_id)
        if 'error' in post_info or not post_info.get('id'):
            await callback.answer("Ошибка: не удалось получить вопрос после создания!")
            return

        # Новый блок: если есть темы, показываем кнопки с темами
        hashtags_env = os.getenv('ASK_HASHTAGS', '')
        hashtags = [h.strip() for h in hashtags_env.split(';') if h.strip()]
        if hashtags:
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text=f"#{h}", callback_data=f"set_theme_{post_info['id']}_{h}")] for h in hashtags
                ] + [
                    [InlineKeyboardButton(text="Отклонить", callback_data=f"reject_{post_info['id']}")]
                ]
            )
            await callback.message.edit_text(
                text=f"Выберите тему для вопроса:",
                reply_markup=keyboard,
                parse_mode="HTML"
            )
            await callback.answer("Выберите тему для вопроса")
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
            admin_message_text = f"🚀 <b>Анонимный вопрос опубликован и оплачен</b>\n\n"
            admin_message_text += f"<b>Автор:</b> <code>{user_id}</code> @{author_username}\n"
            admin_message_text += f"<b>Имя:</b> {author_firstname} {author_lastname}\n"
            admin_message_text += f"<b>Уровень:</b> {author_level}\n"
            admin_message_text += f"<b>Баланс:</b> {author_balance} т.\n"
            admin_message_text += f"<b>Содержание:</b> {post_info.get('content', '')[:100]}{'...' if len(post_info.get('content', '')) > 100 else ''}\n\n"
            admin_message_text += f"<b>Оплата:</b>\n"
            admin_message_text += f"<b>Уровень автора:</b> {author_level}\n"
            admin_message_text += f"<b>Токенов выплачено:</b> {tokens_added}\n"
            admin_message_text += f"<b>Новый баланс автора:</b> {publish_result.get('author_balance', 'N/A')} т.\n\n"
            admin_message_text += f"<b>ID вопроса:</b> {post_info['id']}\n"
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
            # Создаём кнопки для управления постом
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="Отклонить", callback_data=f"reject_{post_info['id']}")],
                    [InlineKeyboardButton(text="Опубликовать сейчас", callback_data=f"publish_now_{post_info['id']}")]
                ]
            )
            admin_message_text = f"#незапостчено\n🕒 <b>Анонимный вопрос поставлен в очередь</b>\n\n"
            admin_message_text += f"<b>Автор:</b> <code>{user_id}</code> @{author_username}\n"
            admin_message_text += f"<b>Имя:</b> {author_firstname} {author_lastname}\n"
            admin_message_text += f"<b>Уровень:</b> {author_level}\n"
            admin_message_text += f"<b>Баланс:</b> {author_balance} т.\n"
            admin_message_text += f"<b>Содержание:</b> {post_content[:100]}{'...' if len(post_content) > 100 else ''}\n\n"
            admin_message_text += f"<b>Статус:</b> В очереди\n"
            admin_message_text += f"<b>Позиция в очереди:</b> {queue_position}\n"
            admin_message_text += f"<b>Время публикации:</b> {scheduled_time_str}\n"
            admin_message_text += f"<b>ID вопроса:</b> {post_info['id']}\n"
            admin_message_text += f"<b>Админ:</b> {callback.from_user.username or callback.from_user.first_name}"
            admin_message_text = re.sub(r"#незапостчено", "#запостчено", admin_message_text)
            await callback.message.edit_text(text=admin_message_text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer("Вопрос обработан")

    @dp.callback_query(F.data.startswith(("publish_now_",)))
    async def publish_now_callback(callback: types.CallbackQuery):
        """Обработчик кнопки 'Опубликовать сейчас' - немедленно публикует пост и оплачивает его"""
        try:
            telegram_id = int(callback.data.split("_")[2])
        except (IndexError, ValueError, AttributeError):
            await callback.answer("Ошибка: не удалось определить id вопроса")
            return
        post_info = await get_post_by_telegram_id(telegram_id)
        if not post_info or 'error' in post_info:
            await callback.message.answer("❌ Ошибка: вопрос не найден в базе данных")
            return
        
        # Сразу отвечаем на callback, чтобы избежать timeout
        await callback.answer("🚀 Публикуем вопрос...")
        
        try:
            logging.info(f"[publish_now_callback] Processing immediate publication for user_id={post_info.get('author')}, telegram_id={telegram_id}")
            
            # Проверяем, что вопрос еще не опубликован
            if post_info.get('is_posted', False):
                await callback.message.answer("❌ Вопрос уже опубликован!")
                return
            
            # Проверяем, что вопрос еще не оплачен
            if post_info.get('is_paid', False):
                await callback.message.answer("❌ Вопрос уже оплачен!")
                return
            
            # Немедленно публикуем вопрос и обрабатываем оплату
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
            await send_publication_and_payment_notification(callback.bot, post_info.get('author'), post_info.get('content', ''), tokens_added, publish_result.get('author_balance', 'N/A'), channel_message_id)
            
            # Убираем кнопки и показываем результат
            await callback.message.delete_reply_markup()
            
            # Получаем подробную инфу об авторе
            author_info = await get_user_info(post_info.get('author'))
            author_username = author_info.get('username', 'N/A')
            author_firstname = author_info.get('firstname', '')
            author_lastname = author_info.get('lastname', '')
            author_level = author_info.get('level', 'N/A')
            author_balance = author_info.get('balance', 'N/A')
            # Сообщение для админов
            admin_message_text = f"🚀 <b>Анонимный вопрос опубликован и оплачен</b>\n\n"
            admin_message_text += f"<b>Автор:</b> <code>{post_info['author']}</code> @{author_username}\n"
            admin_message_text += f"<b>Имя:</b> {author_firstname} {author_lastname}\n"
            admin_message_text += f"<b>Уровень:</b> {author_level}\n"
            admin_message_text += f"<b>Баланс:</b> {author_balance} т.\n"
            admin_message_text += f"<b>Содержание:</b> {post_info.get('content', '')[:100]}{'...' if len(post_info.get('content', '')) > 100 else ''}\n\n"
            admin_message_text += f"<b>Оплата:</b>\n"
            admin_message_text += f"<b>Уровень автора:</b> {author_level}\n"
            admin_message_text += f"<b>Токенов выплачено:</b> {tokens_added}\n"
            admin_message_text += f"<b>Новый баланс автора:</b> {publish_result.get('author_balance', 'N/A')} т.\n\n"
            admin_message_text += f"<b>ID вопроса:</b> {post_info['id']}\n"
            admin_message_text += f"<b>Время публикации:</b> {datetime.now(timezone(timedelta(hours=3))).strftime('%d.%m.%Y в %H:%M')}\n"
            admin_message_text += f"<b>Админ:</b> {callback.from_user.username or callback.from_user.first_name}"
            admin_message_text = re.sub(r"#незапостчено", "#запостчено", admin_message_text)
            
            # Редактируем сообщение в админ чате
            await callback.message.edit_text(
                text=admin_message_text,
                parse_mode="HTML"
            )
            
        except Exception as e:
            logging.exception(f"[publish_now_callback] Exception processing immediate publication for user_id={post_info.get('author')}")
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
            
            # Получаем информацию о вопросе по telegram_id (ID оригинального сообщения пользователя)
            post_info = await get_post_by_telegram_id(original_msg.message_id)
            if 'error' in post_info:
                logging.error(f"[pay_callback] Post not found: {post_info['error']}")
                await callback.answer("❌ Ошибка: вопрос не найден в базе данных")
                return
            
            logging.info(f"[pay_callback] Found post: {post_info}")
            
            # Проверяем, что вопрос еще не оплачен
            if post_info.get('is_paid', False):
                await callback.answer("❌ Вопрос уже оплачен!")
                return
            
            # Проверяем, что вопрос выложен в канал
            channel_message_id = post_info.get('channel_message_id')
            if not channel_message_id:
                await callback.answer("❌ Вопрос еще не выложен в канал")
                return
            
            # Получаем информацию об авторе вопроса
            author_id = post_info.get('author')
            if not author_id:
                await callback.answer("❌ Ошибка: у вопроса нет автора")
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
            admin_message_text = f"<b>Анонимный вопрос оплачен</b>\n\n"
            admin_message_text += f"<b>Автор:</b> {author_id}\n"
            admin_message_text += f"<b>Содержание:</b> {post_info.get('content', '')[:100]}{'...' if len(post_info.get('content', '')) > 100 else ''}\n\n"
            admin_message_text += f"<b>Оплата:</b>\n"
            admin_message_text += f"<b>Уровень автора:</b> {author_level}\n"
            admin_message_text += f"<b>Токенов выплачено:</b> {tokens_added}\n"
            admin_message_text += f"<b>Новый баланс автора:</b> {payment_result.get('author_balance', 'N/A')} т.\n\n"
            admin_message_text += f"<b>ID вопроса:</b> {post_info['id']}\n"
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
                f"📝 ID вопроса: {post_info['id']}\n"
                f"📅 Время выплаты: {datetime.now(timezone(timedelta(hours=3))).strftime('%d.%m.%Y в %H:%M')}\n"
                f"👮 Админ: {callback.from_user.username or callback.from_user.first_name}"
            )
            
            logging.info(f"[pay_callback] Successfully processed payment for post {post_info['id']}: level {author_level}, {tokens_added} tokens")
            
            # Уведомление о пополнении баланса уже отправлено в объединенном уведомлении
            
        except Exception as e:
            logging.exception(f"[pay_callback] Exception processing payment for user_id={user_id}")
            await callback.answer("❌ Произошла ошибка при обработке оплаты")

    @dp.callback_query(F.data.startswith("set_theme_"))
    async def set_theme_callback(callback: types.CallbackQuery):
        # Парсим post_id и тему
        try:
            _, _, post_id, *theme_parts = callback.data.split('_')
            theme = '_'.join(theme_parts)
        except Exception:
            await callback.answer('Ошибка: не удалось определить тему')
            return
        # Получаем вопрос
        post_info = await get_post_by_telegram_id(int(post_id))
        if 'error' in post_info:
            await callback.answer('Ошибка: вопрос не найден')
            return
        # Добавляем хештег в начало контента
        content = post_info.get('content', '')
        hashtag_line = f"<i>#{theme}</i>\n\n"
        if not content.startswith(hashtag_line):
            new_content = hashtag_line + content
            # Обновляем вопрос через API (PATCH)
            import aiohttp
            API_BASE = os.getenv('API_BASE', 'http://backend:8000/api/')
            API_URL = f"{API_BASE}ask-posts/{post_id}/"
            headers = {'Content-Type': 'application/json'}
            payload = {"content": new_content}
            async with aiohttp.ClientSession() as session:
                await session.patch(API_URL, json=payload, headers=headers)
        # После выбора темы показываем обычные кнопки управления вопросом
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Отклонить", callback_data=f"reject_{post_id}")],
                [InlineKeyboardButton(text="Опубликовать сейчас", callback_data=f"publish_now_{post_id}")]
            ]
        )
        await callback.message.edit_reply_markup(reply_markup=keyboard)
        await callback.answer(f"Тема установлена: #{theme}")