#!/usr/bin/env python3
"""
Скрипт для создания и применения миграций для системы промокодов
"""

import os
import sys
import subprocess

def run_command(command, cwd=None):
    """Выполняет команду и возвращает результат"""
    try:
        result = subprocess.run(command, shell=True, cwd=cwd, capture_output=True, text=True)
        print(f"Команда: {command}")
        print(f"STDOUT: {result.stdout}")
        if result.stderr:
            print(f"STDERR: {result.stderr}")
        print(f"Код возврата: {result.returncode}")
        return result.returncode == 0
    except Exception as e:
        print(f"Ошибка выполнения команды: {e}")
        return False

def main():
    print("=== Создание миграций для системы промокодов ===")
    
    # Переходим в директорию backend
    backend_dir = "backend"
    if not os.path.exists(backend_dir):
        print(f"Ошибка: директория {backend_dir} не найдена")
        return False
    
    # Создаем миграции
    print("\n1. Создание миграций...")
    if not run_command("python manage.py makemigrations", cwd=backend_dir):
        print("Ошибка при создании миграций")
        return False
    
    # Применяем миграции
    print("\n2. Применение миграций...")
    if not run_command("python manage.py migrate", cwd=backend_dir):
        print("Ошибка при применении миграций")
        return False
    
    print("\n✅ Миграции успешно созданы и применены!")
    print("\nТеперь можно тестировать команды:")
    print("- /addpromo \"test_123\" 50")
    print("- /promo test_123")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 