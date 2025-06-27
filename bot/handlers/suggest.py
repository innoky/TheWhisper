from aiogram import types, F, Dispatcher
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode, ContentType
from datetime import datetime, timedelta
import os
import pytz
from datetime import time
from db.wapi import get_last_post, try_create_post, mark_post_as_posted, mark_post_as_rejected
import logging


ACTIVE_START_HOUR = 10  # 10:00
ACTIVE_END_HOUR = 1     # 01:00 следующего дня
POST_INTERVAL_MINUTES = 30
BOT_NAME = os.getenv("BOT_NAME")

def save_post_to_db(user_id: int, text: str):
    # Заглушка под сохранение в БД
    print(f"[DB] Saved post from {user_id}: {text[:30]}...")


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
            msg = await message.copy_to(os.getenv('OFFERS_CHAT_ID'))
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{message.from_user.id}")],
                    [InlineKeyboardButton(text="✅ Добавить", callback_data=f"approve_{message.from_user.id}")],
                    [InlineKeyboardButton(text="💰 Выплатить", callback_data=f"pay_{message.from_user.id}")]
                ]
            )
            await message.bot.send_message(
                chat_id=os.getenv("OFFERS_CHAT_ID"),
                text=(
                    f"id: {message.from_user.id}\n"
                    f"username: @{message.from_user.username or 'N/A'}\n\n"
                ),
                reply_to_message_id=msg.message_id,
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
    @dp.callback_query(F.data.startswith(("reject_",)))
    async def reject_callback(callback: types.CallbackQuery):
        result = await mark_post_as_rejected(callback.message.reply_to_message.message_id)
        await callback.message.delete_reply_markup()
        await callback.answer("Пост отклонён!", show_alert=True)
    @dp.callback_query(F.data.startswith(("approve_",)))
    async def approve_callback(callback: types.CallbackQuery):
        user_id = int(callback.data.split("_")[1])
        original_msg = callback.message.reply_to_message
        moscow_tz = pytz.timezone('Europe/Moscow')
        now = datetime.now(moscow_tz)
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
        def next_post_time():
            next_time = last_post_dt + timedelta(minutes=POST_INTERVAL_MINUTES)
            if (next_time.hour <= ACTIVE_START_HOUR) and (next_time.hour >= ACTIVE_END_HOUR):
                next_day = now.date() + timedelta(days=1)
                return moscow_tz.localize(datetime.combine(next_day, time(hour=ACTIVE_START_HOUR, minute=0)))
            return next_time
        caption_or_text = (original_msg.text or original_msg.caption or "").strip()
        scheduled_time = next_post_time()
        if not caption_or_text:
            logging.error(f"[approve_callback] Не удалось создать пост: текст пустой. user_id={user_id}, telegram_id={original_msg.message_id}")
            await callback.answer("Ошибка: текст поста пустой!", show_alert=True)
            return
        logging.info(f"[approve_callback] try_create_post payload: author_id={user_id}, content={caption_or_text}, telegram_id={original_msg.message_id}, post_time={scheduled_time}")
        await try_create_post(author_id=user_id, content=caption_or_text, telegram_id=original_msg.message_id, post_time=scheduled_time)
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{user_id}")],
                [InlineKeyboardButton(text="💰 Выплатить", callback_data=f"pay_{user_id}")]
            ]
        )
        await callback.message.edit_reply_markup(reply_markup=keyboard)
        await callback.answer("Пост добавлен в очередь!", show_alert=True)