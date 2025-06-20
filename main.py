import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import BOT_TOKEN
from middlewares.logging import LoggingMiddleware

# Импортируем хендлеры для регистрации
from handlers import start, comment, admin
from handlers.start import register_start_handlers
from handlers.comment import register_comment_handlers
from handlers.admin import register_admin_handlers
from handlers.balance import register_balance_handlers
from handlers.market import register_market_handlers
from handlers.admin_balance import register_admin_balance_handlers

def register_handlers(dp: Dispatcher):
    # Регистрация всех хендлеров
    pass  # Хендлеры регистрируются через декораторы


def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('app.log', mode='a')
        ]
    )
    bot = Bot(token=BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    dp.update.middleware(LoggingMiddleware())
    # Импорт хендлеров уже регистрирует их через декораторы
    register_admin_balance_handlers(dp)
    register_start_handlers(dp)
    register_market_handlers(dp)
    register_balance_handlers(dp)
    register_admin_handlers(dp)
    register_comment_handlers(dp)
    
   
    
    print("Bot started!")
    dp.run_polling(bot, skip_updates=True)

if __name__ == '__main__':
    main() 