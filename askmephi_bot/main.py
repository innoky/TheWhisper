import logging
import os
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from middlewares.logging import LoggingMiddleware
from SugQueue import post_checker
from middlewares.ensure_user import EnsureUserMiddleware

# Импортируем хендлеры для регистрации
from handlers.start import register_start_handlers
from handlers.suggest import register_suggest_handler
from handlers.comment import register_comment_handlers
from handlers.admin import register_admin_handlers
from handlers.market import register_market_handlers
from handlers.account import register_account_handlers
from handlers.help import register_help_handlers
from handlers.promo import register_promo_handlers


def register_handlers(dp: Dispatcher):
    # Регистрация всех хендлеров
    pass  # Хендлеры регистрируются через декораторы


async def queue_worker(bot: Bot):
    """Фоновая задача для обработки очереди"""
    await post_checker(bot)


async def on_startup(bot):
    """Действия при запуске бота"""
    logging.info("Starting queue worker...")
    asyncio.create_task(queue_worker(bot))




def main():
  
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('app.log', mode='a')
        ]
    )
    BOT_TOKEN = os.getenv('ORACLE_BOT_TOKEN')
    if not BOT_TOKEN:
        raise ValueError("ORACLE_BOT_TOKEN environment variable is not set")
    bot = Bot(token=BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    dp.update.middleware(EnsureUserMiddleware())
    dp.message.middleware(EnsureUserMiddleware())
    dp.callback_query.middleware(EnsureUserMiddleware())
    dp.update.middleware(LoggingMiddleware())
    
    # Импорт хендлеров уже регистрирует их через декораторы
    register_comment_handlers(dp)
    register_admin_handlers(dp)  # Админские команды
    register_promo_handlers(dp)
   
    register_help_handlers(dp)   # Объединенная команда help
    register_start_handlers(dp)
    register_market_handlers(dp)
    register_account_handlers(dp)
    register_suggest_handler(dp)
    
    
    print("Bot started!")
    dp.startup.register(on_startup)
    dp.run_polling(bot, skip_updates=True)

if __name__ == '__main__':
    main()