from aiogram import types, Dispatcher
from aiogram.filters import Command
from config import ADMIN_CHAT_ID
from db.session import AsyncSessionLocal
from db.models import User
from sqlalchemy import select, or_
import datetime

try:
    from sqlalchemy import func
    has_levenshtein = True
except ImportError:
    has_levenshtein = False


def register_admin_balance_handlers(dp: Dispatcher):
    @dp.message(Command("setbalance"))
    async def set_balance_handler(message: types.Message):
        if message.chat.id != ADMIN_CHAT_ID:
            return
        args = message.text.split()
        if len(args) != 3 or not args[1].isdigit() or not args[2].isdigit():
            await message.answer("❌ Использование: /setbalance <user_id> <amount>")
            return
        user_id = int(args[1])
        amount = int(args[2])
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            if not user:
                await message.answer(f"❌ Пользователь с id <code>{user_id}</code> не найден.", parse_mode="HTML")
                return
            user.balance = amount
            await session.commit()
            await message.answer(f"✅ Баланс пользователя <code>{user_id}</code> установлен на <b>{amount}</b>.", parse_mode="HTML")

    @dp.message(Command("getbalance"))
    async def get_balance_handler(message: types.Message):
        if message.chat.id != ADMIN_CHAT_ID:
            return
        args = message.text.split()
        if len(args) != 2 or not args[1].isdigit():
            await message.answer("❌ Использование: /getbalance <user_id>")
            return
        user_id = int(args[1])
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            if not user:
                await message.answer(f"❌ Пользователь с id <code>{user_id}</code> не найден.", parse_mode="HTML")
                return
            reg_date = "—"
            if hasattr(user, "created_at") and user.created_at:
                try:
                    reg_date = datetime.datetime.fromtimestamp(int(user.created_at)).strftime("%d.%m.%Y %H:%M")
                except Exception:
                    reg_date = str(user.created_at)
            await message.answer(
                f"<b>ℹ️ Информация о пользователе</b>\n"
                f"ID: <code>{user.id}</code>\n"
                f"Username: <code>{user.username or '—'}</code>\n"
                f"First name: <code>{user.firstname or '—'}</code>\n"
                f"Last name: <code>{user.lastname or '—'}</code>\n"
                f"Баланс: <b>{user.balance}</b>\n"
                f"Зарегистрирован: <code>{reg_date}</code>",
                parse_mode="HTML"
            )

    @dp.message(Command("getid"))
    async def get_id_handler(message: types.Message):
        if message.chat.id != ADMIN_CHAT_ID:
            return
        args = message.text.split()
        if len(args) != 2:
            await message.answer("❌ Использование: /getid <username>")
            return
        username = args[1].lstrip('@').lower()
        async with AsyncSessionLocal() as session:
            # Поиск по ILIKE и (если есть) по Levenshtein <= 2
            query = select(User).where(
                or_(
                    func.lower(User.username).ilike(f"%{username}%"),
                    func.lower(User.firstname).ilike(f"%{username}%"),
                    func.lower(User.lastname).ilike(f"%{username}%")
                )
            )
            result = await session.execute(query)
            users = result.scalars().all()
            if not users:
                await message.answer("❌ Пользователь не найден.")
                return
            msg = "<b>🔎 Найденные пользователи:</b>\n\n"
            for user in users:
                reg_date = "—"
                if hasattr(user, "created_at") and user.created_at:
                    try:
                        reg_date = datetime.datetime.fromtimestamp(int(user.created_at)).strftime("%d.%m.%Y %H:%M")
                    except Exception:
                        reg_date = str(user.created_at)
                msg += (
                    f"ID: <code>{user.id}</code>\n"
                    f"Username: <code>{user.username or '—'}</code>\n"
                    f"First name: <code>{user.firstname or '—'}</code>\n"
                    f"Last name: <code>{user.lastname or '—'}</code>\n"
                    f"Баланс: <b>{user.balance}</b>\n"
                    f"Зарегистрирован: <code>{reg_date}</code>\n\n"
                )
            await message.answer(msg, parse_mode="HTML")

    @dp.message(Command("unban"))
    async def unban_handler(message: types.Message):
        if message.chat.id != ADMIN_CHAT_ID:
            return
        args = (message.text or '').split()
        if len(args) != 2 or not args[1].isdigit():
            await message.answer("❌ Использование: /unban <user_id>")
            return
        user_id = int(args[1])
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            if not user:
                await message.answer(f"❌ Пользователь с id <code>{user_id}</code> не найден.", parse_mode="HTML")
                return
            user.is_banned = False
            await session.commit()
            await message.answer(f"✅ Пользователь <code>{user_id}</code> разбанен!", parse_mode="HTML") 