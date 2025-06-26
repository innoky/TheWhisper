import logging
import os
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from middlewares.logging import LoggingMiddleware
from SugQueue import post_checker

# Импортируем хендлеры для регистрации

from handlers.start import register_start_handlers
from handlers.suggest import register_suggest_handler
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
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    bot = Bot(token=BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    dp.update.middleware(LoggingMiddleware())
    # Импорт хендлеров уже регистрирует их через декораторы
    register_start_handlers(dp)
    register_suggest_handler(dp)
    print("Bot started!")
    # dp.startup.register(on_startup)
    dp.run_polling(bot, skip_updates=True)

if __name__ == '__main__':
    main()