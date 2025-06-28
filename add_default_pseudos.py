#!/usr/bin/env python3
import asyncio
import os
import sys

# Добавляем путь к модулям бота
sys.path.append(os.path.join(os.path.dirname(__file__), 'bot'))

from db.wapi import add_pseudo_name
import logging

# Настраиваем логирование
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def add_default_pseudos():
    """Добавляет псевдонимы по умолчанию в базу данных"""
    
    default_pseudos = [
        {"pseudo": "Потный щитпостер", "price": 0.0, "is_available": True},
        {"pseudo": "Секси имошница", "price": 0.0, "is_available": True},
        {"pseudo": "Призрак Т-корпуса", "price": 0.0, "is_available": True}
    ]
    
    print("=== Добавление псевдонимов по умолчанию ===")
    
    for pseudo_data in default_pseudos:
        print(f"\nДобавляем псевдоним: {pseudo_data['pseudo']}")
        result = await add_pseudo_name(
            pseudo=pseudo_data['pseudo'],
            price=pseudo_data['price'],
            is_available=pseudo_data['is_available']
        )
        
        if 'id' in result:
            print(f"✅ Успешно добавлен псевдоним '{pseudo_data['pseudo']}' с ID {result['id']}")
        else:
            print(f"❌ Ошибка при добавлении псевдонима '{pseudo_data['pseudo']}': {result}")

if __name__ == "__main__":
    asyncio.run(add_default_pseudos()) 