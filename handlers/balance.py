from aiogram import types, Dispatcher
from aiogram.enums import ParseMode
from aiogram.filters import Command
from db.session import AsyncSessionLocal
from db.models import User
from sqlalchemy import select


def register_balance_handlers(dp: Dispatcher):
    @dp.message(Command("balance"))
    async def balance_handler(message: types.Message):
        if not message.from_user:
            await message.answer("Ошибка: не удалось определить пользователя.")
            return
        user_id = message.from_user.id
        print("TEST")
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            if user:
                balance = user.balance if user.balance is not None else 0
                await message.answer(
                    f"👤 <b>Пользователь:</b> <code>{user.username or 'Без имени'}</code>\n\n"
                    f"<b>🪙 Ваш баланс:</b> <code>{balance}</code>\n\n"
                    f"<i>*Токены можно потратить на преобретение кастомных ников на маркете ( /market ). \nТокены начисляются админами за ваши посты в канале, которые набрали большое количество реакций и комментариев</i>",
                    parse_mode=ParseMode.HTML
                )
            else:
                await message.answer(
                    "Пользователь не найден в базе. Попробуйте сначала оставить комментарий, чтобы зарегистрироваться."
                ) 