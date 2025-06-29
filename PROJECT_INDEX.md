# TheWhisper Project Index

## Project Overview
TheWhisper is a Telegram bot application with a Django backend API for managing pseudo names and user interactions.

## Project Structure

### Root Directory
- `PROJECT_INDEX.md` - This comprehensive project index file
- `add_default_pseudos.py` - Script to add default pseudo names to the database
- `test_pseudo_functions.py` - Test script for pseudo name functionality
- `test_scheduling_logic.py` - Test script for scheduling logic
- `docker-compose.yml` - Docker Compose configuration for the entire project
- `.gitignore` - Git ignore rules

### Bot Directory (`/bot`)
Main Telegram bot application built with aiogram.

#### Core Files
- `main.py` - Main bot entry point and initialization
- `SugQueue.py` - Suggestion queue management system (16KB, 277 lines)
- `requirements.txt` - Python dependencies for the bot
- `Dockerfile` - Docker configuration for the bot
- `PAYMENT_SYSTEM.md` - Documentation for the payment system

#### Handlers (`/bot/handlers`)
Telegram bot message and callback handlers.

- `market.py` - Market functionality for buying pseudo names (11KB, 186 lines)
- `suggest.py` - Suggestion system for posts and content (35KB, 583 lines)
- `comment.py` - Comment system functionality (26KB, 430 lines)
- `admin.py` - Administrative commands and functions (38KB, 730 lines)
- `start.py` - Start command and user onboarding (3KB, 60 lines)
- `start_old.py` - Legacy start command implementation (5.5KB, 98 lines)
- `help.py` - Help system and documentation (5.9KB, 82 lines)
- `account.py` - User account management (6.8KB, 124 lines)

#### Keyboards (`/bot/keyboards`)
Telegram bot keyboard layouts.

- `reply.py` - Reply keyboard builders and layouts (1.7KB, 49 lines)

#### Database (`/bot/db`)
Database interaction layer.

- `wapi.py` - Web API client for database operations (60KB, 1185 lines)

#### Middlewares (`/bot/middlewares`)
Bot middleware components.

- `logging.py` - Logging middleware (176B, 6 lines)

#### Assets (`/bot/assets`)
Static assets and configuration.

- `messages.json` - Message templates and text content (479B, 6 lines)

### Backend Directory (`/backend`)
Django REST API backend application.

#### Core Files
- `manage.py` - Django management script
- `requirements.txt` - Python dependencies for the backend
- `Dockerfile` - Docker configuration for the backend
- `db.sqlite3` - SQLite database file
- `add_pseudos.py` - Script to add pseudo names
- `add_test_pseudos.py` - Script to add test pseudo names

#### API App (`/backend/api`)
Main Django application for the API.

- `views.py` - API views and endpoints (14KB, 318 lines)
- `models.py` - Database models (4.3KB, 109 lines)
- `serializers.py` - Django REST framework serializers (1.6KB, 39 lines)
- `urls.py` - URL routing configuration (545B, 13 lines)
- `admin.py` - Django admin configuration (63B, 4 lines)
- `tests.py` - Test cases (60B, 4 lines)
- `apps.py` - Django app configuration (138B, 7 lines)

##### Management Commands (`/backend/api/management/commands`)
Django management commands.

##### Migrations (`/backend/api/migrations`)
Database migration files.

#### Django Settings (`/backend/thewhisper`)
Django project configuration.

- `settings.py` - Django settings configuration (4.1KB, 150 lines)
- `urls.py` - Main URL routing (814B, 24 lines)
- `wsgi.py` - WSGI application entry point (397B, 17 lines)
- `asgi.py` - ASGI application entry point (397B, 17 lines)

#### Static Files (`/backend/static`)
Static file serving.

- `rest_framework/` - Django REST framework static files
- `admin/` - Django admin static files

### Frontend Directory (`/frontend`)
Frontend application (currently empty).

### Virtual Environment (`/venv`)
Python virtual environment directory.

## Key Features

### Bot Features
1. **Market System** - Users can buy pseudo names
2. **Suggestion System** - Content suggestion and queue management
3. **Comment System** - User commenting functionality
4. **Admin Panel** - Administrative commands and user management
5. **Account Management** - User account and profile management
6. **Payment Integration** - Payment system for purchasing pseudo names

### Backend Features
1. **REST API** - Django REST framework API
2. **Database Models** - User, pseudo name, and content models
3. **Admin Interface** - Django admin for data management
4. **Management Commands** - Custom Django management commands

## Technology Stack

### Bot
- **Framework**: aiogram (Telegram Bot API)
- **Language**: Python
- **Database**: SQLite (via Django API)
- **Containerization**: Docker

### Backend
- **Framework**: Django + Django REST Framework
- **Language**: Python
- **Database**: SQLite
- **Containerization**: Docker

### Infrastructure
- **Orchestration**: Docker Compose
- **Version Control**: Git

## File Size Summary
- **Largest Files**:
  - `bot/db/wapi.py` (60KB, 1185 lines) - Database API client
  - `bot/handlers/admin.py` (38KB, 730 lines) - Admin functionality
  - `bot/handlers/suggest.py` (35KB, 583 lines) - Suggestion system
  - `bot/handlers/comment.py` (26KB, 430 lines) - Comment system
  - `bot/SugQueue.py` (16KB, 277 lines) - Queue management
  - `backend/api/views.py` (14KB, 318 lines) - API views
  - `bot/handlers/market.py` (11KB, 186 lines) - Market system

## Development Status
- **Bot**: Fully implemented with comprehensive functionality
- **Backend**: Django API implemented with models and views
- **Frontend**: Not implemented (empty directory)
- **Infrastructure**: Docker configuration ready

## Recent Changes
- Fixed HTML parsing issues in market.py handler
- Added proper parse_mode=ParseMode.HTML for all HTML-formatted messages
- Removed HTML tags from show_alert callback responses (not supported by Telegram API) 