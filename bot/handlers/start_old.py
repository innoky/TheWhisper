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
        else:
            await message.answer(
                text = "<b>🙏 Добро пожаловать в ядерный бот!</b>\n\nЕсли вы хотите отправить свой пост в предложку - просто отправьте его в этот чат. Администрация рассмотрит содержимое и если все хорошо, то обязательно опубликует его!\n\n<i>Также мы выдаем токены для приобретения кастомных ников для анонимных комментариев</i>\n\n<b>Доступные команды:</b>\n• /account - ваш профиль и баланс токенов\n• /market - магазин никнеймов (оплата токенами)\n• /help - справка по командам",
                parse_mode=ParseMode.HTML)
            return
        
    @dp.message(Command("help"))
    async def help_handler(message: types.Message):
        """Показывает справку по командам для обычных пользователей"""
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
       