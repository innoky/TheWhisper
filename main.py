import os
import logging
import random

from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import CommandStart
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv

load_dotenv('.env')
BOT_TOKEN = os.getenv('BOT_TOKEN')
TARGET_CHAT_ID = int(os.getenv('TARGET_CHAT_ID'))
ADMIN_CHAT_ID = int(os.getenv('ADMIN_CHAT_ID'))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log', mode='a')
    ]
)


from aiogram.client.default import DefaultBotProperties

BLACKLIST_FILE = "blacklist.txt"

def load_blacklist():
    if not os.path.exists(BLACKLIST_FILE):
        return set()
    with open(BLACKLIST_FILE, "r") as f:
        return set(line.strip() for line in f if line.strip().isdigit())

def add_to_blacklist(user_id: int):
    with open(BLACKLIST_FILE, "a") as f:
        f.write(f"{user_id}\n")


bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

storage = MemoryStorage()
dp = Dispatcher(storage=storage)

class LoggingMiddleware:
    async def __call__(self, handler, event, data):
        logging.info(f"Update: {event}")
        return await handler(event, data)


dp.update.middleware(LoggingMiddleware())


class CommentState(StatesGroup):
    waiting_for_comment = State()


def funny_prefix():
    adj_list = open("adj_list.txt", "r", encoding="utf-8").read().splitlines()
    obj_list = open("obj_list.txt", "r", encoding="utf-8").read().splitlines()
    adj = random.choice(adj_list)
    obj = random.choice(obj_list)
    result = adj + " " + obj + " пришёл и оставил комментарий:"
    return result

@dp.message(CommandStart(deep_link=True))
async def start_handler(message: types.Message, state: FSMContext):
    param = message.text.replace("/start ", "")

    if not param.isdigit():
        await message.answer("⚠️ Неверная ссылка. Сообщение не существует.")
        return

    await state.set_state(CommentState.waiting_for_comment)
    await state.update_data(target_message_id=int(param))

    cancel_kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Отмена")]],
        resize_keyboard=True
    )

    await message.answer(
        "✍️ Напиши свой анонимный комментарий к посту.\n\n Отправка стикеров и медиа пока что отсуствует.",
        reply_markup=cancel_kb
    )

@dp.message(F.text.lower() == "отмена", CommentState.waiting_for_comment)
async def cancel_comment(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("🚫 Комментирование отменено.", reply_markup=ReplyKeyboardRemove())


@dp.message(CommentState.waiting_for_comment)
async def handle_anonymous_comment(message: types.Message, state: FSMContext):
    blacklist = load_blacklist()
    if str(message.from_user.id) in blacklist:
        await message.answer("🚫 Вы забанены и не можете оставлять комментарии.")
        await state.clear()
        return
    else:
        data = await state.get_data()
        target_message_id = data.get("target_message_id")

        if not target_message_id:
            await message.answer("❌ Ошибка. Сообщение не найдено.")
            await state.clear()
            return
        fun_pref = funny_prefix()
        text = f"<b>{fun_pref}</b>" + "\n\n" + message.text

        try:
            msg = await bot.send_message(
                chat_id=TARGET_CHAT_ID,
                text=text,
                reply_to_message_id=target_message_id,
                allow_sending_without_reply=True,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
            )

            reply_in_bot_link = f'<a href="https://t.me/mephposterbot?start={msg.message_id}">Ответить</a>'

            await msg.edit_text(
                text=text + f"\n\n<blockquote><b>{reply_in_bot_link}</b></blockquote>",
                disable_web_page_preview = True,
            )


            ban_keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="🚫 Забанить", callback_data=f"ban_{message.from_user.id}")]
                ]
            )
            await bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=f"От: @{message.from_user.username}, {message.from_user.id}, {message.from_user.first_name}, {message.from_user.last_name}\nК посту: t.me/c/2882054542/{target_message_id}\n\n{message.text}",
                reply_markup=ban_keyboard
            )
            await message.answer("✅ Комментарий опубликован анонимно!", reply_markup=ReplyKeyboardRemove())
        except Exception as e:
            logging.exception("❌ Ошибка при отправке комментария:")
            await message.answer("❌ Не удалось опубликовать комментарий. Возможно, пост удалён.",
                                reply_markup=ReplyKeyboardRemove())

    await state.clear()

@dp.callback_query(F.data.startswith("ban_"))
async def handle_ban(callback: types.CallbackQuery):
    user_id = callback.data.replace("ban_", "")
    if not user_id.isdigit():
        await callback.answer("❌ Некорректный ID")
        return

    add_to_blacklist(int(user_id))
    await callback.answer("✅ Пользователь забанен.")
    await callback.message.edit_text(callback.message.text + "\n\n🚫 Пользователь забанен.")

@dp.message()
async def fallback(message: types.Message):
    if message.from_user.first_name == "Telegram":
        comment_url = f"https://t.me/mephposterbot?start={message.message_id}"
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="💬 Комментировать", url=comment_url)]
            ]
        )
        await message.reply(
            "Теперь вы можете оставить анонимный комментарий к этому посту тут:",
            reply_markup=keyboard
            )# --- Main ---
if __name__ == '__main__':
    dp.run_polling(bot, skip_updates=True)
