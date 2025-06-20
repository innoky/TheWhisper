from aiogram import types, F, Dispatcher
from db.session import AsyncSessionLocal
from db.models import User
from sqlalchemy import update, select


def register_admin_handlers(dp: Dispatcher):
    @dp.callback_query(F.data.startswith("ban_"))
    async def handle_ban(callback: types.CallbackQuery):
        if not callback.data:
            await callback.answer("❌ Нет данных для бана")
            return
        user_id = callback.data.replace("ban_", "")
        if not user_id.isdigit():
            await callback.answer("❌ Некорректный ID")
            return
        user_id = int(user_id)
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            if not user:
                await callback.answer("❌ Пользователь не найден.", show_alert=True)
                return
            user.is_banned = True
            await session.commit()
        await callback.answer("✅ Пользователь забанен.")
        msg = getattr(callback, "message", None)
        if msg is not None and getattr(msg, "text", None) is not None:
            await msg.edit_text(msg.text + "\n\n🚫 Пользователь забанен.") 