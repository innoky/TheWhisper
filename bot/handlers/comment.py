from aiogram import types, F, Dispatcher
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.enums import ParseMode
from aiogram.types import ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart

import json
from pathlib import Path

import logging
from db.wapi import leave_anon_comment, get_user_pseudo_names_full, is_user_banned, ensure_user_has_default_pseudos, get_comment_by_telegram_id, send_comment_reply_notification
import os
from keyboards.reply import build_nick_choice_keyboard
from keyboards.reply import cancel_kb


NICKS_PER_PAGE = 5
CHAT_ID = os.getenv("CHAT_ID")
TARGET_CHAT_ID = os.getenv("TARGET_CHAT_ID")
BOT_NAME = os.getenv("BOT_NAME")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")

# Проверяем, что все необходимые переменные окружения установлены
if not all([CHAT_ID, TARGET_CHAT_ID, BOT_NAME, ADMIN_CHAT_ID]):
    raise ValueError("Не все необходимые переменные окружения установлены: CHAT_ID, TARGET_CHAT_ID, BOT_NAME, ADMIN_CHAT_ID")

def get_channel_id_for_link():
    """Возвращает CHAT_ID без префикса -100 для использования в ссылках"""
    if not CHAT_ID:
        return ""
    if CHAT_ID.startswith('-100'):
        return CHAT_ID[4:]  # Убираем префикс -100
    return CHAT_ID

def format_username(username):
    if not username or str(username).lower() == 'none':
        return 'N/A'
    return username

class CommentState(StatesGroup):
    waiting_for_comment = State()
    waiting_for_nick = State()



def register_comment_handlers(dp: Dispatcher):
    @dp.message(F.text.lower() == "отмена", CommentState.waiting_for_comment)

    # Отмена комментирования. Кнопка крепится к сообщению высылаемому после /start
    async def cancel_comment(message: types.Message, state: FSMContext):
        await state.clear()
        await message.answer("<b>Комментирование отменено</b>", reply_markup=ReplyKeyboardRemove(), parse_mode=ParseMode.HTML)

    @dp.message(CommentState.waiting_for_comment, F.video)
    async def handle_video(message: types.Message, state: FSMContext):
        logging.info(f"[handle_photo] User {message.from_user.id} trying to comment with photo")

        await message.answer(
            text ="<b>Анонимные комментарии не поддерживают отправку видео</b>\n\nПопробуйте другой формат сообщения",
            parse_mode=ParseMode.HTML)
    @dp.message(CommentState.waiting_for_comment, F.photo)
    async def handle_photo(message: types.Message, state: FSMContext):
        logging.info(f"[handle_photo] User {message.from_user.id} trying to comment with photo")

        # Убеждаемся, что у пользователя есть псевдонимы
        await ensure_user_has_default_pseudos(message.from_user.id)

        pseudo_names = await get_user_pseudo_names_full(message.from_user.id)
        logging.info(f"[handle_photo] User {message.from_user.id} has pseudo_names: {pseudo_names}")
        if not pseudo_names:
            logging.warning(f"[handle_photo] User {message.from_user.id} has no pseudo names after ensuring")
            await message.answer("<b>У вас нет купленных псевдонимов</b>\n\n<blockquote>Купите псевдоним в /market</blockquote>", parse_mode=ParseMode.HTML)
            await state.clear()
            return
        await state.update_data(
            media_type="photo",
            photo=message.photo[-1].file_id if message.photo else None,
            caption=message.caption or "",
            nick_page=0
        )
        # Убираем обычную клавиатуру перед показом inline-клавиатуры
        await message.answer("<i>Теперь выберите ник для публикации комментария:</i>", reply_markup=ReplyKeyboardRemove(), parse_mode=ParseMode.HTML)
        kb = build_nick_choice_keyboard(pseudo_names, page=0)
        await state.set_state(CommentState.waiting_for_nick)
        await message.answer(
            f"<b>Ваша фотография с подписью:</b>\n\n<blockquote>{message.caption or ''}</blockquote>\n\n<b>Выберите псевдоним для публикации:</b>",
            reply_markup=kb,
            parse_mode=ParseMode.HTML
        )

    @dp.message(CommentState.waiting_for_comment, F.animation)
    async def handle_gif(message: types.Message, state: FSMContext):
        data = await state.get_data()
        target_message_id = data.get("target_message_id")
        try:
            if not TARGET_CHAT_ID:
                raise ValueError("TARGET_CHAT_ID не установлен")
            if not message.animation:
                raise ValueError("Animation не найдено")
            msg = await message.bot.send_animation(
                chat_id=TARGET_CHAT_ID,
                animation=message.animation.file_id,
                reply_to_message_id=target_message_id,
                allow_sending_without_reply=True,
            )
            await message.answer(
                f"<b>Анонимная GIF опубликована</b>\n\n<blockquote><b><a href=\"t.me/c/{get_channel_id_for_link()}/{target_message_id}\">Вернуться к обсуждению</a></b></blockquote>",
                reply_markup=ReplyKeyboardRemove(),
                parse_mode=ParseMode.HTML
            )

            # Сохраняем комментарий через API
            comment_result = await leave_anon_comment(telegram_id=msg.message_id, reply_to=target_message_id, user_id=message.from_user.id, content="[GIF]")
            logging.info(f"[handle_gif] Comment saved to DB: {comment_result}")

            # Отправка в админ-чат с кнопкой Забанить
            ban_keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="Забанить", callback_data=f"ban_{message.from_user.id}")]
                ]
            )
            if not ADMIN_CHAT_ID:
                raise ValueError("ADMIN_CHAT_ID не установлен")
            await message.bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=f"От: @{format_username(message.from_user.username)}, {message.from_user.id}, {message.from_user.first_name}, {message.from_user.last_name}\nК посту: t.me/c/{get_channel_id_for_link()}/{target_message_id}\n\n[GIF]",
                reply_markup=ban_keyboard,
                parse_mode=ParseMode.HTML
            )

            # Проверяем, является ли это ответом на другой комментарий
            if target_message_id and 'error' not in comment_result:
                logging.info(f"[handle_gif] Checking if comment {target_message_id} is a reply to another comment")

                # Получаем информацию о комментарии, на который отвечаем
                original_comment = await get_comment_by_telegram_id(target_message_id)
                logging.info(f"[handle_gif] Original comment data: {original_comment}")

                # Проверяем, что получили валидный комментарий с автором
                if 'error' not in original_comment and original_comment.get('author'):
                    original_author_id = original_comment['author']
                    original_content = original_comment.get('content', '')

                    logging.info(f"[handle_gif] Found original comment author: {original_author_id}")
                    logging.info(f"[handle_gif] Original content: {original_content}")

                    # Отправляем уведомление автору оригинального комментария
                    logging.info(f"[handle_gif] Sending notification to user {original_author_id}")
                    await send_comment_reply_notification(
                        bot=message.bot,
                        original_comment_author_id=original_author_id,
                        original_comment_content=original_content,
                        reply_telegram_id=msg.message_id,
                        reply_content="[GIF]"
                    )
                    logging.info(f"[handle_gif] Reply notification sent to user {original_author_id} for comment {target_message_id}")
                else:
                    logging.info(f"[handle_gif] No valid original comment found: {original_comment}")
            else:
                logging.info(f"[handle_gif] No target_message_id or comment save error, skipping reply notification")

        except Exception as e:
            logging.exception("❌ Ошибка при отправке гифки:")
            await message.answer("❌ <b>Не удалось опубликовать гифку.</b>", reply_markup=ReplyKeyboardRemove(), parse_mode=ParseMode.HTML)
        await state.clear()

    @dp.message(CommentState.waiting_for_comment, F.sticker)
    async def handle_sticker(message: types.Message, state: FSMContext):
        data = await state.get_data()
        target_message_id = data.get("target_message_id")
        try:
            if not TARGET_CHAT_ID:
                raise ValueError("TARGET_CHAT_ID не установлен")
            if not message.sticker:
                raise ValueError("Sticker не найден")
            msg = await message.bot.send_sticker(
                chat_id=TARGET_CHAT_ID,
                sticker=message.sticker.file_id,
                reply_to_message_id=target_message_id,
                allow_sending_without_reply=True,
            )
            await message.answer(
                f"<b>Анонимный стикер опубликован</b>\n\n<blockquote><b><a href=\"t.me/c/{get_channel_id_for_link()}/{target_message_id}\">Вернуться к обсуждению</a></b></blockquote>",
                reply_markup=ReplyKeyboardRemove(),
                parse_mode=ParseMode.HTML
            )

            # Сохраняем комментарий через API
            comment_result = await leave_anon_comment(telegram_id=msg.message_id, reply_to=target_message_id, user_id=message.from_user.id, content="[STICKER]")
            logging.info(f"[handle_sticker] Comment saved to DB: {comment_result}")

            # Отправка в админ-чат с кнопкой Забанить
            ban_keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="Забанить", callback_data=f"ban_{message.from_user.id}")]
                ]
            )
            if not ADMIN_CHAT_ID:
                raise ValueError("ADMIN_CHAT_ID не установлен")
            await message.bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=f"От: @{format_username(message.from_user.username)}, {message.from_user.id}, {message.from_user.first_name}, {message.from_user.last_name}\nК посту: t.me/c/{get_channel_id_for_link()}/{target_message_id}\n\n[STICKER]",
                reply_markup=ban_keyboard,
                parse_mode=ParseMode.HTML
            )

            # Проверяем, является ли это ответом на другой комментарий
            if target_message_id and 'error' not in comment_result:
                logging.info(f"[handle_sticker] Checking if comment {target_message_id} is a reply to another comment")

                # Получаем информацию о комментарии, на который отвечаем
                original_comment = await get_comment_by_telegram_id(target_message_id)
                logging.info(f"[handle_sticker] Original comment data: {original_comment}")

                # Проверяем, что получили валидный комментарий с автором
                if 'error' not in original_comment and original_comment.get('author'):
                    original_author_id = original_comment['author']
                    original_content = original_comment.get('content', '')

                    logging.info(f"[handle_sticker] Found original comment author: {original_author_id}")
                    logging.info(f"[handle_sticker] Original content: {original_content}")

                    # Отправляем уведомление автору оригинального комментария
                    logging.info(f"[handle_sticker] Sending notification to user {original_author_id}")
                    await send_comment_reply_notification(
                        bot=message.bot,
                        original_comment_author_id=original_author_id,
                        original_comment_content=original_content,
                        reply_telegram_id=msg.message_id,
                        reply_content="[STICKER]"
                    )
                    logging.info(f"[handle_sticker] Reply notification sent to user {original_author_id} for comment {target_message_id}")
                else:
                    logging.info(f"[handle_sticker] No valid original comment found: {original_comment}")
            else:
                logging.info(f"[handle_sticker] No target_message_id or comment save error, skipping reply notification")

        except Exception as e:
            logging.exception("❌ Ошибка при отправке стикера:")
            await message.answer("❌ <b>Не удалось опубликовать стикер.</b>", reply_markup=ReplyKeyboardRemove(), parse_mode=ParseMode.HTML)
        await state.clear()

    @dp.message(CommentState.waiting_for_comment, F.text)
    async def handle_comment_text(message: types.Message, state: FSMContext):
        logging.info(f"[handle_comment_text] User {message.from_user.id} trying to comment with text")
        if message.text.startswith("/start"):
              
            current_dir = Path(__file__).parent  # bot/handlers/
            assets_dir = current_dir.parent / "assets"  # поднимаемся на уровень выше и идем в assets
            messages_path = assets_dir / "messages.json"


            with open(messages_path, "r", encoding="utf-8") as f:
                messages = json.load(f)
            param = message.text.replace("/start ", "")
            await state.update_data(target_message_id=int(param))
            await message.answer(
                text=messages['request_comment']['text'].format(rules_url="https://telegra.ph/Pravila-anonimnyh-kommentariev-06-17"),
                reply_markup = cancel_kb,
                parse_mode=ParseMode.HTML,
            )
            
        elif await is_user_banned(message.from_user.id):
            await message.answer("<b>Вы забанены и не можете оставлять комментарии</b>", parse_mode=ParseMode.HTML)
            await state.clear()
            return
        else:
        # Убеждаемся, что у пользователя есть псевдонимы
            await ensure_user_has_default_pseudos(message.from_user.id)

            pseudo_names = await get_user_pseudo_names_full(message.from_user.id)
            logging.info(f"[handle_comment_text] User {message.from_user.id} has pseudo_names: {pseudo_names}")
            if not pseudo_names:
                logging.warning(f"[handle_comment_text] User {message.from_user.id} has no pseudo names after ensuring")
                await message.answer("<b>У вас нет купленных псевдонимов</b>\n\n<blockquote>Купите псевдоним в /market</blockquote>", parse_mode=ParseMode.HTML)
                await state.clear()
                return
            await state.update_data(
                media_type="text",
                comment_text=message.text,
                nick_page=0
            )
            # Убираем обычную клавиатуру перед показом inline-клавиатуры
            await message.answer("<i>Теперь выберите ник для публикации комментария:</i>", reply_markup=ReplyKeyboardRemove(), parse_mode=ParseMode.HTML)
            kb = build_nick_choice_keyboard(pseudo_names, page=0)
            await state.set_state(CommentState.waiting_for_nick)
            await message.answer(
                f"<b>Ваш комментарий:</b>\n\n<blockquote>{message.text}</blockquote>\n\n<b>Выберите псевдоним для публикации:</b>",
                reply_markup=kb,
                parse_mode=ParseMode.HTML
            )

    @dp.callback_query(F.data.startswith("nickpage_"), CommentState.waiting_for_nick)
    async def nick_page_callback(callback: types.CallbackQuery, state: FSMContext):
        data = await state.get_data()
        try:
            page = int(callback.data.replace("nickpage_", ""))
        except Exception:
            page = 0
        pseudo_names = await get_user_pseudo_names_full(callback.from_user.id)
        kb = build_nick_choice_keyboard(pseudo_names, page=page)
        await state.update_data(nick_page=page)
        await callback.message.edit_reply_markup(reply_markup=kb)
        await callback.answer()

    @dp.callback_query(F.data.startswith("choose_nick_"), CommentState.waiting_for_nick)
    async def choose_nick_callback(callback: types.CallbackQuery, state: FSMContext):
        data = await state.get_data()
        pseudo_name_id = int(callback.data.replace("choose_nick_", ""))
        target_message_id = data.get("target_message_id")
        pseudo_names = await get_user_pseudo_names_full(callback.from_user.id)
        pseudo_name = next((pn for pn in pseudo_names if pn[0] == pseudo_name_id), None)
        media_type = data.get("media_type")

        if media_type == "text":
            comment_text = data.get("comment_text")
            text = f"<b>{pseudo_name[1]} оставил(а) комментарий:</b>\n\n{comment_text}"
            try:
                msg = await callback.bot.send_message(
                    chat_id=TARGET_CHAT_ID,
                    text=text,
                    reply_to_message_id=target_message_id,
                    allow_sending_without_reply=True,
                    parse_mode=ParseMode.HTML,
                    disable_web_page_preview=True,
                )
                reply_in_bot_link = f'<a href="https://t.me/{BOT_NAME}?start={msg.message_id}">💬  Ответить</a>'
                await msg.edit_text(
                    text=text + f"\n\n<blockquote><b>{reply_in_bot_link}</b></blockquote>",
                    disable_web_page_preview=True,
                    parse_mode=ParseMode.HTML,
                )
                await callback.message.edit_reply_markup(reply_markup=None)
                await callback.message.answer(
                    f"<b>Комментарий опубликован анонимно</b>\n\n<blockquote><b><a href=\"t.me/c/{get_channel_id_for_link()}/{target_message_id}\">Вернуться к обсуждению</a></b></blockquote>",
                    reply_markup=ReplyKeyboardRemove(),
                    parse_mode=ParseMode.HTML
                )
                # Сохраняем комментарий через новый API
                comment_result = await leave_anon_comment(telegram_id=msg.message_id, reply_to=target_message_id, user_id=callback.from_user.id, content=comment_text)
                logging.info(f"[choose_nick_callback] Comment saved to DB: {comment_result}")

                # Отправка в админ-чат с кнопкой Забанить
                ban_keyboard = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="Забанить", callback_data=f"ban_{callback.from_user.id}")]
                    ]
                )
                await callback.bot.send_message(
                    chat_id=ADMIN_CHAT_ID,
                    text=f"От: @{format_username(callback.from_user.username)}, {callback.from_user.id}, {callback.from_user.first_name}, {callback.from_user.last_name}\nК посту: t.me/c/{get_channel_id_for_link()}/{target_message_id}\n\n{comment_text}",
                    reply_markup=ban_keyboard,
                    parse_mode=ParseMode.HTML
                )

                # Проверяем, является ли это ответом на другой комментарий
                if target_message_id and 'error' not in comment_result:
                    logging.info(f"[choose_nick_callback] Checking if comment {target_message_id} is a reply to another comment")

                    # Получаем информацию о комментарии, на который отвечаем
                    original_comment = await get_comment_by_telegram_id(target_message_id)
                    logging.info(f"[choose_nick_callback] Original comment data: {original_comment}")

                    # Проверяем, что получили валидный комментарий с автором
                    if 'error' not in original_comment and original_comment.get('author'):
                        original_author_id = original_comment['author']
                        original_content = original_comment.get('content', '')

                        logging.info(f"[choose_nick_callback] Found original comment author: {original_author_id}")
                        logging.info(f"[choose_nick_callback] Original content: {original_content}")

                        # Отправляем уведомление автору оригинального комментария (включая самого себя)
                        logging.info(f"[choose_nick_callback] Sending notification to user {original_author_id}")
                        await send_comment_reply_notification(
                            bot=callback.bot,
                            original_comment_author_id=original_author_id,
                            original_comment_content=original_content,
                            reply_telegram_id=msg.message_id,
                            reply_content=comment_text
                        )
                        logging.info(f"[choose_nick_callback] Reply notification sent to user {original_author_id} for comment {target_message_id}")
                    else:
                        logging.info(f"[choose_nick_callback] No valid original comment found: {original_comment}")
                else:
                    logging.info(f"[choose_nick_callback] No target_message_id or comment save error, skipping reply notification")

            except Exception as e:
                logging.exception("Ошибка при отправке комментария:")
                await callback.message.answer("<b>Не удалось опубликовать комментарий. Возможно, пост удален</b>", reply_markup=ReplyKeyboardRemove(), parse_mode=ParseMode.HTML)
            await state.clear()
            await callback.answer("Комментарий отправлен!")
        elif media_type == "photo":
            photo = data.get("photo")
            caption = data.get("caption")
            text = f"<b>{pseudo_name[1]} пришёл и оставил комментарий:</b>\n\n{caption}"
            try:
                msg = await callback.bot.send_photo(
                    chat_id=TARGET_CHAT_ID,
                    photo=photo,
                    caption=text,
                    reply_to_message_id=target_message_id,
                    allow_sending_without_reply=True,
                    parse_mode=ParseMode.HTML,
                )
                await callback.message.edit_reply_markup(reply_markup=None)
                await callback.message.answer(
                    f"<b>Комментарий опубликован анонимно</b>\n\n<blockquote><b><a href=\"t.me/c/{get_channel_id_for_link()}/{target_message_id}\">Вернуться к обсуждению</a></b></blockquote>",
                    reply_markup=ReplyKeyboardRemove(),
                    parse_mode=ParseMode.HTML
                )
                # Сохраняем комментарий через API
                content_for_db = f"[PHOTO] {caption}" if caption else "[PHOTO]"
                comment_result = await leave_anon_comment(telegram_id=msg.message_id, reply_to=target_message_id, user_id=callback.from_user.id, content=content_for_db)
                logging.info(f"[choose_nick_callback] Photo comment saved to DB: {comment_result}")

                # Отправка в админ-чат с кнопкой Забанить
                ban_keyboard = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="Забанить", callback_data=f"ban_{callback.from_user.id}")]
                    ]
                )
                await callback.bot.send_message(
                    chat_id=ADMIN_CHAT_ID,
                    text=f"От: @{format_username(callback.from_user.username)}, {callback.from_user.id}, {callback.from_user.first_name}, {callback.from_user.last_name}\nК посту: t.me/c/{get_channel_id_for_link()}/{target_message_id}\n\n{caption}",
                    reply_markup=ban_keyboard,
                    parse_mode=ParseMode.HTML
                )

                # Проверяем, является ли это ответом на другой комментарий
                if target_message_id and 'error' not in comment_result:
                    logging.info(f"[choose_nick_callback] Checking if photo comment {target_message_id} is a reply to another comment")

                    # Получаем информацию о комментарии, на который отвечаем
                    original_comment = await get_comment_by_telegram_id(target_message_id)
                    logging.info(f"[choose_nick_callback] Original comment data: {original_comment}")

                    # Проверяем, что получили валидный комментарий с автором
                    if 'error' not in original_comment and original_comment.get('author'):
                        original_author_id = original_comment['author']
                        original_content = original_comment.get('content', '')

                        logging.info(f"[choose_nick_callback] Found original comment author: {original_author_id}")
                        logging.info(f"[choose_nick_callback] Original content: {original_content}")

                        # Отправляем уведомление автору оригинального комментария
                        logging.info(f"[choose_nick_callback] Sending notification to user {original_author_id}")
                        await send_comment_reply_notification(
                            bot=callback.bot,
                            original_comment_author_id=original_author_id,
                            original_comment_content=original_content,
                            reply_telegram_id=msg.message_id,
                            reply_content=content_for_db
                        )
                        logging.info(f"[choose_nick_callback] Reply notification sent to user {original_author_id} for comment {target_message_id}")
                    else:
                        logging.info(f"[choose_nick_callback] No valid original comment found: {original_comment}")
                else:
                    logging.info(f"[choose_nick_callback] No target_message_id or comment save error, skipping reply notification")

            except Exception as e:
                logging.exception("Ошибка при отправке комментария:")
                await callback.message.answer("<b>Не удалось опубликовать комментарий. Возможно, пост удален</b>", reply_markup=ReplyKeyboardRemove(), parse_mode=ParseMode.HTML)
            await state.clear()
            await callback.answer("Комментарий отправлен!")

        