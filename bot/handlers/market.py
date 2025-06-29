from aiogram import types, F, Dispatcher
from aiogram.enums import ParseMode
from db.wapi import get_all_pseudo_names, purchase_pseudo_name_with_payment
from keyboards.reply import build_market_keyboard
import logging
import asyncio

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
        logging.info(f"[market_handler] User {message.from_user.id} requested /market")
        pseudos = await get_all_pseudo_names()
        
        # Проверяем, что получили список, а не ошибку
        if isinstance(pseudos, dict) and pseudos.get("error"):
            logging.error(f"[market_handler] Error getting pseudos: {pseudos.get('error')}")
            await message.answer(f'<b>Ошибка получения псевдонимов:</b> {pseudos.get("error", "Неизвестная ошибка")}', parse_mode=ParseMode.HTML)
            return
        
        if not isinstance(pseudos, list):
            logging.error(f"[market_handler] Unexpected pseudos format: {type(pseudos)}")
            await message.answer('<b>Неожиданный формат данных от сервера</b>', parse_mode=ParseMode.HTML)
            return
        
        if not pseudos:
            logging.warning("[market_handler] No pseudos available")
            await message.answer('<b>В базе данных нет доступных псевдонимов.</b>\n\n<blockquote>Обратитесь к администратору</blockquote>', parse_mode=ParseMode.HTML)
            return
            
        available = [p for p in pseudos if p.get('is_available', True)]
        logging.info(f"[market_handler] Available pseudos: {[p['id'] for p in available]}")
        
        if not available:
            logging.warning("[market_handler] No available pseudos after filtering")
            await message.answer('<b>Нет доступных для покупки псевдонимов</b>', parse_mode=ParseMode.HTML)
            return
            
        from db.wapi import get_user_pseudo_names
        user_pseudo_ids = await get_user_pseudo_names(message.from_user.id)
        # user_pseudo_ids теперь список id
        logging.info(f"[market_handler] User {message.from_user.id} has pseudo_ids: {user_pseudo_ids}")
        logging.info(f"[market_handler] Available pseudos: {[p['id'] for p in available]}")
        filtered = [p for p in available if int(p['id']) not in user_pseudo_ids]
        logging.info(f"[market_handler] Filtered pseudos: {[p['id'] for p in filtered]}")
        if not filtered:
            logging.info(f"[market_handler] User {message.from_user.id} has no available pseudos to buy")
            await message.answer('<b>У вас нет доступных для покупки псевдонимов</b>\n\n<blockquote>Вы уже купили все доступные псевдонимы</blockquote>', parse_mode=ParseMode.HTML)
            return
        kb = build_market_keyboard(filtered, page=0)
        await message.answer('<b>Доступные псевдонимы:</b>', reply_markup=kb, parse_mode=ParseMode.HTML)

    @dp.callback_query(F.data.startswith("market_page_"))
    async def market_page_callback(callback: types.CallbackQuery):
        page = int(callback.data.replace("market_page_", ""))
        pseudos = await get_all_pseudo_names()
        
        # Проверяем, что получили список, а не ошибку
        if isinstance(pseudos, dict) and pseudos.get("error"):
            await callback.answer(f'<b>Ошибка:</b> {pseudos.get("error", "Неизвестная ошибка")}', parse_mode=ParseMode.HTML)
            return
        
        if not isinstance(pseudos, list):
            await callback.answer('<b>Неожиданный формат данных от сервера</b>', parse_mode=ParseMode.HTML)
            return
        
        if not pseudos:
            await callback.answer('<b>Нет доступных псевдонимов</b>', parse_mode=ParseMode.HTML)
            return
            
        available = [p for p in pseudos if p.get('is_available', True)]
        # Получить список купленных ников пользователя
        from db.wapi import get_user_pseudo_names
        user_pseudo_ids = await get_user_pseudo_names(callback.from_user.id)
        # Фильтруем уже купленные ники
        logging.info(f"[market_page_callback] User {callback.from_user.id} has pseudo_ids: {user_pseudo_ids}")
        logging.info(f"[market_page_callback] Available pseudos: {[p['id'] for p in available]}")
        filtered = [p for p in available if int(p['id']) not in user_pseudo_ids]
        logging.info(f"[market_page_callback] Filtered pseudos: {[p['id'] for p in filtered]}")
        kb = build_market_keyboard(filtered, page=page)
        await callback.message.edit_reply_markup(reply_markup=kb)
        await callback.answer()

    @dp.callback_query(F.data.startswith("market_buy_"))
    async def market_buy_callback(callback: types.CallbackQuery):
        pseudo_id = int(callback.data.replace("market_buy_", ""))
        user_id = callback.from_user.id
        result = await purchase_pseudo_name_with_payment(user_id, pseudo_id)
        
        if result.get('success'):
            pseudo_name = result.get('pseudo_name', 'Unknown')
            price = result.get('price', 0)
            new_balance = result.get('new_balance', 0)
            await callback.answer(f"✅ Никнейм '{pseudo_name}' куплен за {price} т.! Новый баланс: {new_balance} т.", show_alert=True)
            
            # Обновить клавиатуру: убрать купленный ник
            pseudos = await get_all_pseudo_names()
            
            # Проверяем, что получили список, а не ошибку
            if isinstance(pseudos, dict) and pseudos.get("error"):
                await callback.answer(f'❌ Ошибка обновления: {pseudos.get("error", "Неизвестная ошибка")}')
                return
            
            if not isinstance(pseudos, list):
                await callback.answer('❌ Неожиданный формат данных от сервера.')
                return
                
            available = [p for p in pseudos if p.get('is_available', True)]
            # Получить список купленных ников пользователя
            from db.wapi import get_user_pseudo_names
            user_pseudos = await get_user_pseudo_names(user_id)
            user_pseudo_ids = user_pseudos
            logging.info(f"[market_buy_callback] User {user_id} has pseudo_ids: {user_pseudo_ids}")
            logging.info(f"[market_buy_callback] Available pseudos: {[p['id'] for p in available]}")
            
            filtered = [p for p in available if int(p['id']) not in user_pseudo_ids]
            logging.info(f"[market_buy_callback] Filtered pseudos: {[p['id'] for p in filtered]}")
            
            if not filtered:
                # Если больше нет доступных псевдонимов, удаляем клавиатуру
                try:
                    await callback.message.edit_reply_markup(reply_markup=None)
                    await callback.message.edit_text("✅ Никнейм куплен! Больше доступных никнеймов нет.")
                except Exception as e:
                    logging.warning(f"[market_buy_callback] Error updating message: {e}")
                return
            
            kb = build_market_keyboard(filtered, page=0)
            try:
                await callback.message.edit_reply_markup(reply_markup=kb)
            except Exception as e:
                if "message is not modified" in str(e):
                    # Сообщение не изменилось, это нормально
                    logging.info(f"[market_buy_callback] Message not modified (normal)")
                else:
                    logging.warning(f"[market_buy_callback] Error updating keyboard: {e}")
                    # Если не удалось обновить клавиатуру, просто отвечаем
                    await callback.answer("✅ Никнейм куплен! Обновите список командой /market")
                
        elif 'non_field_errors' in result and 'unique' in str(result['non_field_errors']):
            await callback.answer("❌ Вы уже купили этот ник!", show_alert=True)
            # Обновляем клавиатуру, убирая купленный ник
            pseudos = await get_all_pseudo_names()
            
            if isinstance(pseudos, dict) and pseudos.get("error"):
                return
            
            if not isinstance(pseudos, list):
                return
                
            available = [p for p in pseudos if p.get('is_available', True)]
            from db.wapi import get_user_pseudo_names
            user_pseudos = await get_user_pseudo_names(user_id)
            user_pseudo_ids = user_pseudos
            filtered = [p for p in available if int(p['id']) not in user_pseudo_ids]
            
            if not filtered:
                try:
                    await callback.message.edit_reply_markup(reply_markup=None)
                    await callback.message.edit_text("✅ У вас уже есть все доступные никнеймы!")
                except Exception as e:
                    logging.warning(f"[market_buy_callback] Error updating message: {e}")
                return
            
            kb = build_market_keyboard(filtered, page=0)
            try:
                await callback.message.edit_reply_markup(reply_markup=kb)
            except Exception as e:
                if "message is not modified" in str(e):
                    logging.info(f"[market_buy_callback] Message not modified (normal)")
                else:
                    logging.warning(f"[market_buy_callback] Error updating keyboard: {e}")
        else:
            error_msg = result.get('error', str(result)) if result else "Неизвестная ошибка"
            if len(error_msg) > 200:
                error_msg = error_msg[:200] + "..."
            await callback.answer(f"Ошибка: {error_msg}", show_alert=True) 