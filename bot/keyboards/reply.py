from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
 
cancel_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="Отмена")]],
    resize_keyboard=True
)