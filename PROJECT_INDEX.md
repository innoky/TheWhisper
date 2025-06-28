# TheWhisper - Индекс проекта

## Обзор проекта
TheWhisper - это Telegram-бот для анонимной публикации постов с системой модерации, комментариев и токен-экономики. Проект состоит из трех основных компонентов:
- **Bot** - Telegram бот на aiogram
- **Backend** - Django REST API
- **Database** - PostgreSQL

## Структура проекта

### Корневая директория
```
/
├── .git/                    # Git репозиторий
├── .gitignore              # Исключения Git
├── docker-compose.yml      # Docker Compose конфигурация
├── add_default_pseudos.py  # Скрипт добавления псевдонимов
├── test_pseudo_functions.py # Тесты функций псевдонимов
├── test_scheduling_logic.py # Тесты логики планирования
├── venv/                   # Виртуальное окружение Python
├── bot/                    # Telegram бот
├── backend/                # Django API
└── frontend/               # Frontend (пустая директория)
```

### Bot (Telegram бот)

#### Основные файлы
- **`main.py`** (70 строк) - Главный файл бота, инициализация и запуск
- **`SugQueue.py`** (202 строки) - Система очереди постов и публикации в канал
- **`requirements.txt`** (28 зависимостей) - Зависимости бота
- **`Dockerfile`** (14 строк) - Docker образ для бота
- **`PAYMENT_SYSTEM.md`** (85 строк) - Документация платежной системы

#### Handlers (Обработчики команд)
- **`handlers/start.py`** (60 строк) - Обработка команды /start
- **`handlers/suggest.py`** (587 строк) - Основная логика отправки постов
- **`handlers/comment.py`** (322 строки) - Система комментариев
- **`handlers/admin.py`** (462 строки) - Административные команды
- **`handlers/market.py`** (186 строк) - Магазин псевдонимов
- **`handlers/account.py`** (125 строк) - Управление аккаунтом
- **`handlers/help.py`** (96 строк) - Справка и помощь
- **`handlers/start_old.py`** (98 строк) - Старая версия start

#### База данных
- **`db/wapi.py`** (990 строк) - API клиент для взаимодействия с Django backend

#### Интерфейс
- **`keyboards/reply.py`** (49 строк) - Клавиатуры и кнопки
- **`middlewares/logging.py`** (6 строк) - Middleware для логирования
- **`assets/messages.json`** (6 строк) - JSON с сообщениями

### Backend (Django API)

#### Основные файлы
- **`manage.py`** (23 строки) - Django management script
- **`requirements.txt`** (10 зависимостей) - Зависимости backend
- **`Dockerfile`** (17 строк) - Docker образ для backend
- **`db.sqlite3`** (0 байт) - SQLite база (не используется в продакшене)

#### Django приложение
- **`thewhisper/settings.py`** (150 строк) - Настройки Django
- **`thewhisper/urls.py`** (24 строки) - Основные URL маршруты
- **`thewhisper/wsgi.py`** (17 строк) - WSGI конфигурация
- **`thewhisper/asgi.py`** (17 строк) - ASGI конфигурация

#### API приложение
- **`api/models.py`** (109 строк) - Django модели данных
- **`api/views.py`** (279 строк) - API views и бизнес-логика
- **`api/serializers.py`** (39 строк) - Django REST serializers
- **`api/urls.py`** (13 строк) - API URL маршруты
- **`api/admin.py`** (4 строки) - Django admin конфигурация
- **`api/tests.py`** (4 строки) - Тесты API

#### Утилиты
- **`add_pseudos.py`** (51 строка) - Скрипт добавления псевдонимов
- **`add_test_pseudos.py`** (51 строка) - Скрипт добавления тестовых псевдонимов

#### Статические файлы
- **`static/rest_framework/`** - Django REST Framework статика
- **`static/admin/`** - Django Admin статика

## Модели данных

### User
- Основная модель пользователя
- Поля: id, username, firstname, lastname, balance, level, is_admin, is_banned

### Post
- Модель поста
- Поля: author, content, media_type, posted_at, is_rejected, is_posted, telegram_id, channel_message_id, is_paid, paid_at

### Comment
- Модель комментария
- Поля: reply_to, author, content, created_at, telegram_id

### PseudoNames
- Модель псевдонимов в магазине
- Поля: price, pseudo, is_available

### UserPseudoName
- Связь пользователей с купленными псевдонимами
- Поля: user, pseudo_name, purchase_date

### AuthCredential & LoginToken
- Модели для аутентификации

## Основные функции

### Система постов
1. Пользователи отправляют посты боту
2. Посты попадают в чат модерации
3. Админы одобряют/отклоняют посты
4. Одобренные посты планируются в очередь
5. Система автоматически публикует посты в канал
6. После публикации начисляются токены

### Система комментариев
- Анонимные комментарии к постам
- Ответы на комментарии
- Уведомления о новых комментариях

### Токен-экономика
- Начисление токенов за посты (5-50 в зависимости от уровня)
- Покупка псевдонимов за токены
- Система уровней пользователей

### Магазин псевдонимов
- Покупка анонимных псевдонимов
- Использование псевдонимов при комментировании
- Управление псевдонимами админами

## Технологический стек

### Bot
- **aiogram 3.18.0** - Telegram Bot API framework
- **aiohttp** - HTTP клиент
- **psycopg2-binary** - PostgreSQL драйвер
- **Django** - Для работы с API

### Backend
- **Django 5.2.3** - Web framework
- **Django REST Framework 3.16.0** - API framework
- **psycopg2-binary** - PostgreSQL драйвер
- **gunicorn** - WSGI сервер
- **whitenoise** - Статические файлы

### Infrastructure
- **Docker & Docker Compose** - Контейнеризация
- **PostgreSQL 15** - База данных
- **Nginx** (через whitenoise) - Статические файлы

## Конфигурация

### Переменные окружения
- `BOT_TOKEN` - Токен Telegram бота
- `CHANNEL_ID` - ID канала для публикации
- `OFFERS_CHAT_ID` - ID чата модерации
- `DB_NAME`, `DB_USER`, `DB_PASSWORD` - Настройки PostgreSQL

### Временные зоны
- Настроена на Europe/Moscow
- Используется UTC в базе данных

## Архитектура

### Микросервисная архитектура
1. **Bot Service** - Обработка Telegram сообщений
2. **Backend Service** - REST API и бизнес-логика
3. **Database Service** - PostgreSQL

### Коммуникация
- Bot ↔ Backend через HTTP API
- Backend ↔ Database через Django ORM
- Все сервисы в Docker network

### Очередь постов
- Фоновая задача в боте проверяет посты каждые 20 секунд
- Автоматическая публикация по расписанию
- Система уведомлений о статусе постов

## Развертывание

### Docker Compose
```bash
docker-compose up -d
```

### Локальная разработка
```bash
# Backend
cd backend
python manage.py runserver

# Bot
cd bot
python main.py
```

## Мониторинг и логирование
- Логирование в файл `app.log`
- Логирование в stdout для Docker
- Подробные логи API запросов
- Логирование ошибок и исключений 