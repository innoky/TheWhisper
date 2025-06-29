from aiogram import types, F, Dispatcher
from aiogram.enums import ParseMode
from db.wapi import create_promo_code, get_promo_code_by_code, check_user_promo_code_activation, activate_promo_code, add_balance, get_user_info
import logging
import re

def register_promo_handlers(dp: Dispatcher):
    @dp.message(F.text.startswith("/addpromo"))
    async def add_promo_handler(message: types.Message):
        """Обработчик команды /addpromo для создания промокодов (только для админов)"""
        logging.info(f"[add_promo_handler] User {message.from_user.id} requested /addpromo")
        
        # Проверяем, является ли пользователь админом
        user_info = await get_user_info(message.from_user.id)
        if isinstance(user_info, dict) and user_info.get('error'):
            await message.answer(f'<b>Ошибка получения информации о пользователе:</b> {user_info.get("error")}', parse_mode=ParseMode.HTML)
            return
        
        if not user_info.get('is_admin', False):
            await message.answer('<b>У вас нет прав для выполнения этой команды</b>', parse_mode=ParseMode.HTML)
            return
        
        # Парсим команду: /addpromo "promo_name" tokens
        text = message.text.strip()
        match = re.match(r'/addpromo\s+"([^"]+)"\s+(\d+(?:\.\d+)?)', text)
        
        if not match:
            await message.answer(
                '<b>Неверный формат команды!</b>\n\n'
                '<b>Правильный формат:</b>\n'
                '<code>/addpromo "название_промокода" количество_токенов</code>\n\n'
                '<b>Пример:</b>\n'
                '<code>/addpromo "nuke_123" 50</code>',
                parse_mode=ParseMode.HTML
            )
            return
        
        promo_name = match.group(1)
        tokens = float(match.group(2))
        
        # Проверяем валидность названия промокода
        if not re.match(r'^[a-zA-Z0-9_-]+$', promo_name):
            await message.answer(
                '<b>Неверное название промокода!</b>\n\n'
                'Название может содержать только буквы, цифры, дефисы и подчеркивания.',
                parse_mode=ParseMode.HTML
            )
            return
        
        # Проверяем количество токенов
        if tokens <= 0:
            await message.answer('<b>Количество токенов должно быть больше нуля</b>', parse_mode=ParseMode.HTML)
            return
        
        if tokens > 10000:
            await message.answer('<b>Количество токенов не может превышать 10,000</b>', parse_mode=ParseMode.HTML)
            return
        
        # Создаем промокод
        result = await create_promo_code(
            code=promo_name,
            reward_amount=tokens,
            description=f"Промокод создан администратором {message.from_user.id}",
            max_uses=1,  # Каждый пользователь может использовать только один раз
            created_by=message.from_user.id
        )
        
        if isinstance(result, dict) and result.get('error'):
            error_msg = result.get('error', 'Неизвестная ошибка')
            if 'unique' in str(error_msg).lower():
                await message.answer(f'<b>Промокод "{promo_name}" уже существует!</b>', parse_mode=ParseMode.HTML)
            else:
                await message.answer(f'<b>Ошибка создания промокода:</b> {error_msg}', parse_mode=ParseMode.HTML)
            return
        
        await message.answer(
            f'<b>✅ Промокод успешно создан!</b>\n\n'
            f'<b>Название:</b> <code>{promo_name}</code>\n'
            f'<b>Награда:</b> {tokens} т.\n'
            f'<b>Использований:</b> 1 раз на пользователя\n'
            f'<b>Статус:</b> Активен',
            parse_mode=ParseMode.HTML
        )

    @dp.message(F.text.startswith("/promo"))
    async def activate_promo_handler(message: types.Message):
        """Обработчик команды /promo для активации промокодов"""
        logging.info(f"[activate_promo_handler] User {message.from_user.id} requested /promo")
        
        # Парсим команду: /promo promo_name
        text = message.text.strip()
        parts = text.split()
        
        if len(parts) != 2:
            await message.answer(
                '<b>Неверный формат команды!</b>\n\n'
                '<b>Правильный формат:</b>\n'
                '<code>/promo название_промокода</code>\n\n'
                '<b>Пример:</b>\n'
                '<code>/promo nuke_123</code>',
                parse_mode=ParseMode.HTML
            )
            return
        
        promo_name = parts[1]
        
        # Получаем информацию о промокоде
        promo_info = await get_promo_code_by_code(promo_name)
        
        if isinstance(promo_info, dict) and promo_info.get('error'):
            await message.answer(
                f'<b>❌ Промокод "{promo_name}" не найден!</b>\n\n'
                'Проверьте правильность написания промокода.',
                parse_mode=ParseMode.HTML
            )
            return
        
        # Проверяем, активен ли промокод
        if not promo_info.get('is_active', False):
            await message.answer(
                f'<b>❌ Промокод "{promo_name}" неактивен!</b>',
                parse_mode=ParseMode.HTML
            )
            return
        
        # Проверяем, не истек ли срок действия
        if promo_info.get('expires_at'):
            from datetime import datetime, timezone
            expires_at = datetime.fromisoformat(promo_info['expires_at'].replace('Z', '+00:00'))
            if datetime.now(timezone.utc) > expires_at:
                await message.answer(
                    f'<b>❌ Срок действия промокода "{promo_name}" истек!</b>',
                    parse_mode=ParseMode.HTML
                )
                return
        
        # Проверяем, не превышен ли лимит использований
        max_uses = promo_info.get('max_uses', 1)
        current_uses = promo_info.get('current_uses', 0)
        if max_uses > 0 and current_uses >= max_uses:
            await message.answer(
                f'<b>❌ Промокод "{promo_name}" больше недоступен!</b>\n\n'
                f'Лимит использований исчерпан.',
                parse_mode=ParseMode.HTML
            )
            return
        
        # Проверяем, не активировал ли пользователь уже этот промокод
        activation_check = await check_user_promo_code_activation(message.from_user.id, promo_info['id'])
        
        if not isinstance(activation_check, dict) or not activation_check.get('error'):
            # Пользователь уже активировал этот промокод
            await message.answer(
                f'<b>❌ Вы уже активировали промокод "{promo_name}"!</b>\n\n'
                'Каждый промокод можно использовать только один раз.',
                parse_mode=ParseMode.HTML
            )
            return
        
        # Активируем промокод
        activation_result = await activate_promo_code(message.from_user.id, promo_info['id'])
        
        if isinstance(activation_result, dict) and activation_result.get('error'):
            error_msg = activation_result.get('error', 'Неизвестная ошибка')
            logging.error(f"[activate_promo_handler] Activation error: {error_msg}")
            
            # Проверяем специфические ошибки
            if 'unique' in str(error_msg).lower():
                await message.answer(
                    f'<b>❌ Вы уже активировали промокод "{promo_name}"!</b>\n\n'
                    'Каждый промокод можно использовать только один раз.',
                    parse_mode=ParseMode.HTML
                )
            elif 'not-null' in str(error_msg).lower():
                await message.answer(
                    f'<b>❌ Ошибка активации промокода!</b>\n\n'
                    'Техническая ошибка. Обратитесь к администратору.',
                    parse_mode=ParseMode.HTML
                )
            else:
                await message.answer(f'<b>❌ Ошибка активации промокода:</b> {error_msg}', parse_mode=ParseMode.HTML)
            return
        
        # Добавляем токены на баланс пользователя
        reward_amount = promo_info.get('reward_amount', 0)
        balance_result = await add_balance(message.from_user.id, reward_amount)
        
        if isinstance(balance_result, dict) and balance_result.get('error'):
            await message.answer(
                f'<b>⚠️ Промокод активирован, но возникла ошибка при начислении токенов!</b>\n\n'
                f'Обратитесь к администратору.',
                parse_mode=ParseMode.HTML
            )
            return
        
        # Получаем обновленную информацию о пользователе
        user_info = await get_user_info(message.from_user.id)
        new_balance = user_info.get('balance', 0) if not isinstance(user_info, dict) or not user_info.get('error') else 'неизвестно'
        
        await message.answer(
            f'<b>✅ Промокод "{promo_name}" успешно активирован!</b>\n\n'
            f'<b>Награда:</b> +{reward_amount} т.\n'
            f'<b>Новый баланс:</b> {new_balance} т.\n\n'
            f'<i>Спасибо за использование промокода!</i>',
            parse_mode=ParseMode.HTML
        ) 