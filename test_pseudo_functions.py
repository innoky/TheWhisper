#!/usr/bin/env python3
import asyncio
import os
import sys

# Добавляем путь к модулям бота
sys.path.append(os.path.join(os.path.dirname(__file__), 'bot'))

from db.wapi import get_user_pseudo_names, get_user_pseudo_names_full, get_all_pseudo_names
import logging

# Настраиваем логирование
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def test_pseudo_functions():
    # Тестируем с конкретным user_id (замените на реальный ID пользователя)
    test_user_id = 123456789  # Замените на реальный ID
    
    print("=== Тестирование функций работы с никами ===")
    
    print("\n1. Получение всех доступных ников:")
    all_pseudos = await get_all_pseudo_names()
    print(f"Все ники: {all_pseudos}")
    
    print("\n2. Получение ID купленных ников пользователя:")
    user_pseudo_ids = await get_user_pseudo_names(test_user_id)
    print(f"ID купленных ников: {user_pseudo_ids}")
    
    print("\n3. Получение полной информации о купленных никах:")
    user_pseudo_full = await get_user_pseudo_names_full(test_user_id)
    print(f"Полная информация о никах: {user_pseudo_full}")
    
    print("\n4. Проверка фильтрации в маркете:")
    if isinstance(all_pseudos, list):
        available = [p for p in all_pseudos if p.get('is_available', True)]
        print(f"Доступные ники: {[p['id'] for p in available]}")
        print(f"ID купленных ников: {user_pseudo_ids}")
        filtered = [p for p in available if int(p['id']) not in user_pseudo_ids]
        print(f"Отфильтрованные ники: {[p['id'] for p in filtered]}")

if __name__ == "__main__":
    asyncio.run(test_pseudo_functions()) 