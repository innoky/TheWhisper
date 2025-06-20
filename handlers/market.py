from aiogram import types, Dispatcher
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from db.session import get_available_pseudo_names, buy_pseudo_name, AsyncSessionLocal
from db.models import PseudoName, User
from sqlalchemy import select, update
from config import ADMIN_CHAT_ID


def register_market_handlers(dp: Dispatcher):
    @dp.message(Command("market"))
    async def market_handler(message: types.Message):
        if not message.from_user:
            await message.answer("Ошибка: не удалось определить пользователя.")
            return
        user_id = message.from_user.id
        # Получаем баланс пользователя
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            balance = user.balance if user and user.balance is not None else 0
        pseudo_names = await get_available_pseudo_names(user_id)
        # Фильтруем только нераспроданные
        pseudo_names = [pn for pn in pseudo_names if not getattr(pn, 'is_sold', False)]
        if not pseudo_names:
            await message.answer("Все ники уже куплены или магазин пуст.")
            return
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=f"{pn.name} — {pn.cost}💰", callback_data=f"buy_pseudo_{pn.id}")]
                for pn in pseudo_names
            ]
        )
        await message.answer(
            f"<b>🛒 Магазин кастомных имён</b>\n\nВаш баланс: <b>{balance}</b>\n\nВыберите ник для покупки:",
            reply_markup=kb,
            parse_mode=ParseMode.HTML
        )

    @dp.callback_query(lambda c: c.data and c.data.startswith("buy_pseudo_"))
    async def buy_pseudo_callback(callback: types.CallbackQuery):
        if not callback.from_user:
            await callback.answer("Ошибка: не удалось определить пользователя.", show_alert=True)
            return
        user_id = callback.from_user.id
        try:
            pseudo_name_id = int(callback.data.replace("buy_pseudo_", ""))
        except Exception:
            await callback.answer("Ошибка: неверный формат данных.", show_alert=True)
            return
        success, msg = await buy_pseudo_name(user_id, pseudo_name_id)
        await callback.answer(msg, show_alert=True)
        if success:
            await callback.message.edit_text(
                f"✅ {msg}\n\nОбновите /market, чтобы увидеть новые доступные ники.",
                parse_mode=ParseMode.HTML
            )

    @dp.message(Command("addnick"))
    async def add_nick_handler(message: types.Message):
        if message.chat.id != ADMIN_CHAT_ID:
            return
        # Ожидаем /addnick "Example nick" 150
        import re
        match = re.match(r'/addnick\s+"(.+?)"\s+(\d+)', message.text)
        if not match:
            await message.answer('❌ Использование: /addnick "Example nick" 150')
            return
        name = match.group(1).strip()
        cost = int(match.group(2))
        async with AsyncSessionLocal() as session:
            new_nick = PseudoName(name=name, cost=cost, is_sold=False)
            session.add(new_nick)
            await session.commit()
            await message.answer(f'✅ Ник <b>{name}</b> (стоимость: <b>{cost}</b>) добавлен на маркет!', parse_mode="HTML")

    @dp.message(Command("nicks"))
    async def nicks_handler(message: types.Message):
        if message.chat.id != ADMIN_CHAT_ID:
            return
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(PseudoName))
            nicks = result.scalars().all()
            if not nicks:
                await message.answer("Нет ников в базе.")
                return
            msg = "<b>Все ники:</b>\n\n"
            for n in nicks:
                msg += f"ID: <code>{n.id}</code> | <b>{n.name}</b> | Стоимость: <b>{n.cost}</b> | Продан: <b>{'Да' if getattr(n, 'is_sold', False) else 'Нет'}</b>\n"
            await message.answer(msg, parse_mode="HTML")

    @dp.message(Command("sold"))
    async def sold_handler(message: types.Message):
        if message.chat.id != ADMIN_CHAT_ID:
            return
        args = message.text.split()
        if len(args) != 2 or not args[1].isdigit():
            await message.answer("❌ Использование: /sold <nickid>")
            return
        nickid = int(args[1])
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(PseudoName).where(PseudoName.id == nickid))
            nick = result.scalar_one_or_none()
            if not nick:
                await message.answer("❌ Ник не найден.")
                return
            nick.is_sold = True
            await session.commit()
            await message.answer(f"✅ Ник <b>{nick.name}</b> (ID: <code>{nick.id}</code>) отмечен как проданный.", parse_mode="HTML") 