from aiogram import types, F, Dispatcher
from aiogram.enums import ParseMode
from db.wapi import get_all_pseudo_names, purchase_pseudo_name
from keyboards.reply import build_market_keyboard

NICKS_PER_PAGE = 5

# TODO: заменить на реальный API покупки ника
async def try_purchase_pseudo(user_id: int, pseudo_id: int) -> dict:
    # Заглушка: всегда успех
    print(f"purchase_pseudo_name: user_id={user_id} ({type(user_id)}), pseudo_id={pseudo_id} ({type(pseudo_id)})")
    payload = {"user": str(user_id), "pseudo_name": str(pseudo_id)}
    return {"success": True, "pseudo_id": pseudo_id}


def register_market_handlers(dp: Dispatcher):
    @dp.message(F.text == "/market")
    async def market_handler(message: types.Message):
        pseudos = await get_all_pseudo_names()
        if isinstance(pseudos, dict) and pseudos.get("error"):
            await message.answer(f'❌ Ошибка: {pseudos}')
            return
        available = [p for p in pseudos if p.get('is_available', True)]
        from db.wapi import get_user_pseudo_names
        user_pseudo_ids = await get_user_pseudo_names(message.from_user.id)
        # user_pseudo_ids теперь список id
        filtered = [p for p in available if p['id'] not in user_pseudo_ids]
        if not filtered:
            await message.answer('У вас нет доступных для покупки никнеймов.')
            return
        kb = build_market_keyboard(filtered, page=0)
        await message.answer('<b>Доступные никнеймы:</b>', reply_markup=kb, parse_mode=ParseMode.HTML)

    @dp.callback_query(F.data.startswith("market_page_"))
    async def market_page_callback(callback: types.CallbackQuery):
        page = int(callback.data.replace("market_page_", ""))
        pseudos = await get_all_pseudo_names()
        available = [p for p in pseudos if p.get('is_available', True)]
        kb = build_market_keyboard(available, page=page)
        await callback.message.edit_reply_markup(reply_markup=kb)
        await callback.answer()

    @dp.callback_query(F.data.startswith("market_buy_"))
    async def market_buy_callback(callback: types.CallbackQuery):
        pseudo_id = int(callback.data.replace("market_buy_", ""))
        user_id = callback.from_user.id
        result = await purchase_pseudo_name(user_id, pseudo_id)
        if 'id' in result and 'pseudo_name' in result:
            await callback.answer("✅ Никнейм куплен!", show_alert=True)
            # Обновить клавиатуру: убрать купленный ник
            pseudos = await get_all_pseudo_names()
            available = [p for p in pseudos if p.get('is_available', True)]
            # Получить список купленных ников пользователя
            from db.wapi import get_user_pseudo_names
            user_pseudos = await get_user_pseudo_names(user_id)
            user_pseudo_ids = user_pseudos  # теперь это просто список id
            filtered = [p for p in available if p['id'] not in user_pseudo_ids]
            kb = build_market_keyboard(filtered, page=0)
            await callback.message.edit_reply_markup(reply_markup=kb)
        elif 'non_field_errors' in result and 'unique' in str(result['non_field_errors']):
            await callback.answer("❌ Вы уже купили этот ник!", show_alert=True)
        else:
            await callback.answer(f"❌ Ошибка: {result}", show_alert=True) 