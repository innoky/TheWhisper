from aiogram import types, F, Dispatcher
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.enums import ParseMode
from aiogram.types import ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart
from config import TARGET_CHAT_ID, ADMIN_CHAT_ID, BOT_NAME, CHAT_ID
from utils.blacklist import load_blacklist, add_to_blacklist
from db.session import AsyncSessionLocal
from db.models import Comment, PseudoName, UserPseudoName, User
from sqlalchemy import select, update
import logging

NICKS_PER_PAGE = 5

class CommentState(StatesGroup):
    waiting_for_comment = State()
    waiting_for_nick = State()

async def save_comment(msg_id: int, user_id: int, username: str, message: str, timestamp: int):
    async with AsyncSessionLocal() as session:
        async with session.begin():
            session.add(Comment(id=msg_id, user_id=user_id, username=username, message=message, created_at=timestamp))

async def get_user_pseudo_names(user_id: int):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(PseudoName)
            .join(UserPseudoName, PseudoName.id == UserPseudoName.pseudo_name_id)
            .where(UserPseudoName.user_id == user_id)
        )
        return result.scalars().all()

async def is_user_banned(user_id: int):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User.is_banned).where(User.id == user_id))
        row = result.first()
        return bool(row and row[0])

def build_nick_keyboard(pseudo_names, page=0):
    start = page * NICKS_PER_PAGE
    end = start + NICKS_PER_PAGE
    page_nicks = pseudo_names[start:end]
    kb = [
        [InlineKeyboardButton(text=pn.name, callback_data=f"choose_nick_{pn.id}")]
        for pn in page_nicks
    ]
    nav = []
    if start > 0:
        nav.append(InlineKeyboardButton(text="<<", callback_data=f"nickpage_{page-1}"))
    if end < len(pseudo_names):
        nav.append(InlineKeyboardButton(text=">>", callback_data=f"nickpage_{page+1}"))
    if nav:
        kb.append(nav)
    return InlineKeyboardMarkup(inline_keyboard=kb)

def register_comment_handlers(dp: Dispatcher):
    @dp.message(F.text.lower() == "отмена", CommentState.waiting_for_comment)
    async def cancel_comment(message: types.Message, state: FSMContext):
        await state.clear()
        await message.answer("🚫 <b>Комментирование отменено.</b>", reply_markup=ReplyKeyboardRemove(), parse_mode=ParseMode.HTML)

    @dp.message(CommandStart(deep_link=True))
    async def start_handler(message: types.Message, state: FSMContext):
        param = (message.text or "").split(" ", 1)[1] if " " in (message.text or "") else ""
        if not param.isdigit():
            await message.answer("⚠️ <b>Неверная ссылка.</b>\nПроверьте корректность ссылки для комментирования.", parse_mode=ParseMode.HTML)
            return
        if not message.from_user:
            await message.answer("🚫 <b>Ошибка: не удалось определить пользователя.</b>", parse_mode=ParseMode.HTML)
            return
        if await is_user_banned(message.from_user.id):
            await message.answer("🚫 <b>Вы забанены и не можете оставлять комментарии.</b>", parse_mode=ParseMode.HTML)
            return
        await state.set_state(CommentState.waiting_for_comment)
        await state.update_data(target_message_id=int(param))
        await message.answer(
            "✍️ <b>Отправь свой анонимный комментарий</b> (текст, фото, гифку или стикер).\n\n<code>После этого выбери ник для публикации.</code>",
            parse_mode=ParseMode.HTML
        )

    @dp.message(CommentState.waiting_for_comment, F.photo)
    async def handle_photo(message: types.Message, state: FSMContext):
        pseudo_names = await get_user_pseudo_names(message.from_user.id)
        if not pseudo_names:
            await message.answer("⚠️ <b>У вас нет купленных ников.</b>\nКупите ник в /market.", parse_mode=ParseMode.HTML)
            await state.clear()
            return
        await state.update_data(
            media_type="photo",
            photo=message.photo[-1].file_id if message.photo else None,
            caption=message.caption or "",
            nick_page=0
        )
        kb = build_nick_keyboard(pseudo_names, page=0)
        await state.set_state(CommentState.waiting_for_nick)
        await message.answer(
            f"🖼️ <b>Ваша фотография с подписью:</b>\n\n<blockquote>{message.caption or ''}</blockquote>\n\n<b>Выберите ник для публикации:</b>",
            reply_markup=kb,
            parse_mode=ParseMode.HTML
        )

    @dp.message(CommentState.waiting_for_comment, F.animation)
    async def handle_gif(message: types.Message, state: FSMContext):
        data = await state.get_data()
        target_message_id = data.get("target_message_id")
        try:
            await message.bot.send_animation(
                chat_id=TARGET_CHAT_ID,
                animation=message.animation.file_id,
                reply_to_message_id=target_message_id,
                allow_sending_without_reply=True,
            )
            await message.answer(
                f"✅ <b>Анонимная гифка опубликована!</b>\n\n<blockquote><b><a href=\"t.me/c/{CHAT_ID}/{target_message_id}\">Вернуться к обсуждению</a></b></blockquote>",
                reply_markup=ReplyKeyboardRemove(),
                parse_mode=ParseMode.HTML
            )
            # Отправка в админ-чат с кнопкой Забанить
            ban_keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="🚫 Забанить", callback_data=f"ban_{message.from_user.id}")]
                ]
            )
            await message.bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=f"От: @{message.from_user.username}, {message.from_user.id}, {message.from_user.first_name}, {message.from_user.last_name}\nК посту: t.me/c/{CHAT_ID}/{target_message_id}\n\n[GIF]",
                reply_markup=ban_keyboard,
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            logging.exception("❌ Ошибка при отправке гифки:")
            await message.answer("❌ <b>Не удалось опубликовать гифку.</b>", reply_markup=ReplyKeyboardRemove(), parse_mode=ParseMode.HTML)
        await state.clear()

    @dp.message(CommentState.waiting_for_comment, F.sticker)
    async def handle_sticker(message: types.Message, state: FSMContext):
        data = await state.get_data()
        target_message_id = data.get("target_message_id")
        try:
            await message.bot.send_sticker(
                chat_id=TARGET_CHAT_ID,
                sticker=message.sticker.file_id,
                reply_to_message_id=target_message_id,
                allow_sending_without_reply=True,
            )
            await message.answer(
                f"✅ <b>Анонимный стикер опубликован!</b>\n\n<blockquote><b><a href=\"t.me/c/{CHAT_ID}/{target_message_id}\">Вернуться к обсуждению</a></b></blockquote>",
                reply_markup=ReplyKeyboardRemove(),
                parse_mode=ParseMode.HTML
            )
            # Отправка в админ-чат с кнопкой Забанить
            ban_keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="🚫 Забанить", callback_data=f"ban_{message.from_user.id}")]
                ]
            )
            await message.bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=f"От: @{message.from_user.username}, {message.from_user.id}, {message.from_user.first_name}, {message.from_user.last_name}\nК посту: t.me/c/{CHAT_ID}/{target_message_id}\n\n[Sticker]",
                reply_markup=ban_keyboard,
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            logging.exception("❌ Ошибка при отправке стикера:")
            await message.answer("❌ <b>Не удалось опубликовать стикер.</b>", reply_markup=ReplyKeyboardRemove(), parse_mode=ParseMode.HTML)
        await state.clear()

    @dp.message(CommentState.waiting_for_comment, F.text)
    async def handle_comment_text(message: types.Message, state: FSMContext):
        if await is_user_banned(message.from_user.id):
            await message.answer("🚫 <b>Вы забанены и не можете оставлять комментарии.</b>", parse_mode=ParseMode.HTML)
            await state.clear()
            return
        pseudo_names = await get_user_pseudo_names(message.from_user.id)
        if not pseudo_names:
            await message.answer("⚠️ <b>У вас нет купленных ников.</b>\nКупите ник в /market.", parse_mode=ParseMode.HTML)
            await state.clear()
            return
        await state.update_data(
            media_type="text",
            comment_text=message.text,
            nick_page=0
        )
        kb = build_nick_keyboard(pseudo_names, page=0)
        await state.set_state(CommentState.waiting_for_nick)
        await message.answer(
            f"💬 <b>Ваш комментарий:</b>\n\n<blockquote>{message.text}</blockquote>\n\n<b>Выберите ник для публикации:</b>",
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
        pseudo_names = await get_user_pseudo_names(callback.from_user.id)
        kb = build_nick_keyboard(pseudo_names, page=page)
        await state.update_data(nick_page=page)
        await callback.message.edit_reply_markup(reply_markup=kb)
        await callback.answer()

    @dp.callback_query(F.data.startswith("choose_nick_"), CommentState.waiting_for_nick)
    async def choose_nick_callback(callback: types.CallbackQuery, state: FSMContext):
        data = await state.get_data()
        pseudo_name_id = int(callback.data.replace("choose_nick_", ""))
        target_message_id = data.get("target_message_id")
        pseudo_names = await get_user_pseudo_names(callback.from_user.id)
        pseudo_name = next((pn for pn in pseudo_names if pn.id == pseudo_name_id), None)
        media_type = data.get("media_type")
        if media_type == "text":
            comment_text = data.get("comment_text")
            text = f"<b>{pseudo_name.name} пришёл и оставил комментарий:</b>\n\n{comment_text}"
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
                    f"✅ <b>Комментарий опубликован анонимно!</b>\n\n<blockquote><b><a href=\"t.me/c/{CHAT_ID}/{target_message_id}\">Вернуться к обсуждению</a></b></blockquote>",
                    reply_markup=ReplyKeyboardRemove(),
                    parse_mode=ParseMode.HTML
                )
                # Отправка в админ-чат с кнопкой Забанить
                ban_keyboard = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="🚫 Забанить", callback_data=f"ban_{callback.from_user.id}")]
                    ]
                )
                await callback.bot.send_message(
                    chat_id=ADMIN_CHAT_ID,
                    text=f"От: @{callback.from_user.username}, {callback.from_user.id}, {callback.from_user.first_name}, {callback.from_user.last_name}\nК посту: t.me/c/{CHAT_ID}/{target_message_id}\n\n{comment_text}",
                    reply_markup=ban_keyboard,
                    parse_mode=ParseMode.HTML
                )
            except Exception as e:
                logging.exception("❌ Ошибка при отправке комментария:")
                await callback.message.answer("❌ <b>Не удалось опубликовать комментарий. Возможно, пост удалён.</b>", reply_markup=ReplyKeyboardRemove(), parse_mode=ParseMode.HTML)
            await state.clear()
            await callback.answer("Комментарий отправлен!", show_alert=True)
        elif media_type == "photo":
            photo = data.get("photo")
            caption = data.get("caption")
            text = f"<b>{pseudo_name.name} пришёл и оставил комментарий:</b>\n\n{caption}"
            try:
                await callback.bot.send_photo(
                    chat_id=TARGET_CHAT_ID,
                    photo=photo,
                    caption=text,
                    reply_to_message_id=target_message_id,
                    allow_sending_without_reply=True,
                    parse_mode=ParseMode.HTML,
                )
                await callback.message.answer(
                    f"✅ <b>Комментарий опубликован анонимно!</b>\n\n<blockquote><b><a href=\"t.me/c/{CHAT_ID}/{target_message_id}\">Вернуться к обсуждению</a></b></blockquote>",
                    reply_markup=ReplyKeyboardRemove(),
                    parse_mode=ParseMode.HTML
                )
                # Отправка в админ-чат с кнопкой Забанить
                ban_keyboard = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="🚫 Забанить", callback_data=f"ban_{callback.from_user.id}")]
                    ]
                )
                await callback.bot.send_message(
                    chat_id=ADMIN_CHAT_ID,
                    text=f"От: @{callback.from_user.username}, {callback.from_user.id}, {callback.from_user.first_name}, {callback.from_user.last_name}\nК посту: t.me/c/{CHAT_ID}/{target_message_id}\n\n{caption}",
                    reply_markup=ban_keyboard,
                    parse_mode=ParseMode.HTML
                )
            except Exception as e:
                logging.exception("❌ Ошибка при отправке комментария:")
                await callback.message.answer("❌ <b>Не удалось опубликовать комментарий. Возможно, пост удалён.</b>", reply_markup=ReplyKeyboardRemove(), parse_mode=ParseMode.HTML)
            await state.clear()
            await callback.answer("Комментарий отправлен!", show_alert=True)

    @dp.message()
    async def fallback(message: types.Message):
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