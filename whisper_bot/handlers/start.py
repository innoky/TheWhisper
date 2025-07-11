from aiogram import types, F, Dispatcher
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.enums import ParseMode


import json
from pathlib import Path
from db.wapi import try_create_user
from keyboards.reply import cancel_kb
from handlers.comment import CommentState
import random

def register_start_handlers(dp: Dispatcher):
    @dp.message(CommandStart())
    async def start_handler(message: types.Message, state: FSMContext):
        
        current_dir = Path(__file__).parent  # bot/handlers/
        assets_dir = current_dir.parent / "assets"  # поднимаемся на уровень выше и идем в assets
        messages_path = assets_dir / "messages.json"


        with open(messages_path, "r", encoding="utf-8") as f:
            messages = json.load(f)

        param = message.text.replace("/start ", "")
        await try_create_user(
            message.from_user.id, 
            message.from_user.username, 
            message.from_user.first_name,
            message.from_user.last_name
            )
    
        # await get_or_create_user(
        #     user_id = message.from_user.id,
        #     username = message.from_user.username or "",
        #     firstname = message.from_user.first_name or "",
        #     lastname = message.from_user.last_name or "",
        # )
        print(param)
        if (not param.isdigit() and len(param)<=1) :
            await message.answer(
                text="<b>⚠️ Похоже что-то пошло не так</b> \n\nЛибо у нас баг, либо вы хулиганите. Ай-ай-ай",
                parse_mode=ParseMode.HTML)
            return
        elif (param.isdigit()):
            await state.set_state(CommentState.waiting_for_comment)
            await state.update_data(target_message_id=int(param))
            await message.answer(
                text=messages['request_comment']['text'].format(rules_url="https://telegra.ph/Pravila-anonimnyh-kommentariev-06-17"),
                reply_markup=cancel_kb,
                parse_mode=ParseMode.HTML,
            ) 
            chance = random.randint(1,10)
            if chance > 5:
                await message.answer(
                    text = "<b>У нас открылся канал с вопросами!</b>\n\nТеперь вы можете задать свой вопрос в нашем втором канале - @askmephi - и получить на него ответ. \n\nПосты там публикуются чаще, поэтому если требуется задать срочный вопрос делайте это там!",
                    parse_mode=ParseMode.HTML
                )
        else:
            await message.answer(
                text = "<b>Добро пожаловать в TheWhisper</b>\n\n<blockquote>Отправляйте посты в этот чат для рассмотрения администрацией. Качественный контент будет опубликован в канале с начислением токенов.\n\nСистема токенов позволяет приобретать псевдонимы для анонимных комментариев.</blockquote>\n\n<b>Основные команды:</b>\n• /account — профиль и баланс\n• /market — магазин псевдонимов\n• /help — справка",
                parse_mode=ParseMode.HTML)
            return 