import asyncio
from aiogram import Bot, Dispatcher
import time
import os
import datetime
from db.wapi import get_recent_posts, mark_post_as_posted


async def publish_to_channel(post, bot) -> bool:
    """Публикует пост в Telegram-канал (заглушка)"""
    try:
        fci = os.getenv("OFFERS_CHAT_ID")
        mi = post["telegram_id"]
        ci = os.getenv("CHANNEL_ID")
        print(fci,mi,ci)
        await bot.copy_message(
            from_chat_id=os.getenv("OFFERS_CHAT_ID"),
            message_id=post["telegram_id"],
            chat_id=os.getenv("CHANNEL_ID")
            )

        return True
    except Exception as e:
        print(f"Ошибка публикации: {e}")
        return False


async def mark_as_posted(post_id: int) -> None:
    """Помечает пост как опубликованный в БД (заглушка)"""
    await mark_post_as_posted(post_id)
    print(f"Помечаю пост {post_id} как опубликованный")

async def post_checker(bot):
    """Основной цикл проверки постов"""
    while True:
        try:
            # Создаем текущее время с часовым поясом UTC
            now = datetime.datetime.now(datetime.timezone.utc)
            posts = await get_recent_posts()
            
            for post in posts:
                if post['is_posted']:
                    continue
                if post['is_rejected']:
                    continue
                    
                posted_at = datetime.datetime.fromisoformat(post['posted_at'])
                # Если время из БД без пояса - добавляем UTC
                if posted_at.tzinfo is None:
                    posted_at = posted_at.replace(tzinfo=datetime.timezone.utc)
                # Если с поясом - конвертируем в UTC
                else:
                    posted_at = posted_at.astimezone(datetime.timezone.utc)
                
                time_diff = (now - posted_at).total_seconds()
                print(time_diff)
                # Проверяем разницу во времени (оригинальное условие: < 60 часов)
                if 0 <= abs(time_diff) < 60 * 60 * 60:
                    success = await publish_to_channel(post, bot)
                    if success:
                        await mark_as_posted(post['id'])
        
        except Exception as e:
            print(f"Ошибка в цикле проверки: {e}")
        
        await asyncio.sleep(20)