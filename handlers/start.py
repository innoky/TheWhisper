from aiogram import types, F, Dispatcher
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.enums import ParseMode
from keyboards.reply import cancel_kb
from db.session import AsyncSessionLocal, get_or_create_user

class CommentState(StatesGroup):
    waiting_for_comment = State()

def register_start_handlers(dp: Dispatcher):
    @dp.message(CommandStart(deep_link=True))
    async def start_handler(message: types.Message, state: FSMContext):
        param = message.text.replace("/start ", "")
        await get_or_create_user(
            user_id = message.from_user.id,
            username = message.from_user.username or "",
            firstname = message.from_user.first_name or "",
            lastname = message.from_user.last_name or "",
        )
        if not param.isdigit():
            await message.answer("⚠️ Неверная ссылка. Сообщение не существует.")
            return
        await state.set_state(CommentState.waiting_for_comment)
        await state.update_data(target_message_id=int(param))
        await message.answer(
            '✍️<b> Напиши свой анонимный комментарий к посту</b>\n\nОтправка стикеров и медиа пока что отсуствует. \n\nПользуясь ботом вы автоматически соглашаетесь с <a href="https://telegra.ph/Pravila-anonimnyh-kommentariev-06-17">правилами пользования</a>',
            reply_markup=cancel_kb,
            parse_mode=ParseMode.HTML,
        ) 