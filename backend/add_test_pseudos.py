#!/usr/bin/env python3
import os
import sys
import django

# Добавляем путь к проекту
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Настраиваем Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'thewhisper.settings')
django.setup()

from api.models import PseudoNames

def add_test_pseudos():
    """Добавляет тестовые псевдонимы в базу данных"""
    
    # Список тестовых псевдонимов
    test_pseudos = [
        {"pseudo": "Аноним", "price": 10.0, "is_available": True},
        {"pseudo": "Тайный", "price": 15.0, "is_available": True},
        {"pseudo": "Скрытный", "price": 20.0, "is_available": True},
        {"pseudo": "Невидимый", "price": 25.0, "is_available": True},
        {"pseudo": "Загадочный", "price": 30.0, "is_available": True},
        {"pseudo": "Мистический", "price": 35.0, "is_available": True},
        {"pseudo": "Темный", "price": 40.0, "is_available": True},
        {"pseudo": "Светлый", "price": 45.0, "is_available": True},
    ]
    
    for pseudo_data in test_pseudos:
        # Проверяем, существует ли уже такой псевдоним
        existing = PseudoNames.objects.filter(pseudo=pseudo_data["pseudo"]).first()
        if existing:
            print(f"Псевдоним '{pseudo_data['pseudo']}' уже существует")
        else:
            # Создаем новый псевдоним
            pseudo = PseudoNames.objects.create(
                pseudo=pseudo_data["pseudo"],
                price=pseudo_data["price"],
                is_available=pseudo_data["is_available"]
            )
            print(f"Добавлен псевдоним: {pseudo.pseudo} (цена: {pseudo.price})")
    
    # Показываем все псевдонимы
    all_pseudos = PseudoNames.objects.all()
    print(f"\nВсего псевдонимов в базе: {all_pseudos.count()}")
    for pseudo in all_pseudos:
        print(f"- {pseudo.pseudo} (цена: {pseudo.price}, доступен: {pseudo.is_available})")

if __name__ == "__main__":
 