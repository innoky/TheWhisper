import asyncio
from aiogram import Bot, Dispatcher
import time
import os
import datetime
from datetime import timezone, timedelta
from db.wapi import get_recent_posts, mark_post_as_posted, update_post_channel_info, get_user_info, process_post_payment, recalculate_queue_after_immediate_publication


async def send_publication_notification(bot: Bot, post: dict, channel_message_id: int):
    """Отправляет уведомление пользователю о публикации поста"""
    try:
        author_id = post.get('author')
        if not author_id:
            print(f"[send_publication_notification] No author_id in post {post.get('id')}")
            return
        
        # Получаем информацию о пользователе
        user_info = await get_user_info(author_id)
        if 'error' in user_info:
            print(f"[send_publication_notification] Error getting user info: {user_info['error']}")
            return
        
        # Формируем ссылку на пост в канале
        channel_id = os.getenv("CHANNEL_ID")
        if not channel_id:
            print(f"[send_publication_notification] CHANNEL_ID not set")
            return
            
        if channel_id.startswith('-100'):
            channel_id = channel_id[4:]  # Убираем префикс -100 для ссылки
        
        post_link = f"https://t.me/c/{channel_id}/{channel_message_id}"
        
        # Формируем сообщение
        notification_text = f"🎉 <b>Ваш пост опубликован!</b>\n\n"
        notification_text += f"📝 <b>Содержание:</b>\n"
        notification_text += f"<i>{post.get('content', '')[:100]}{'...' if len(post.get('content', '')) > 100 else ''}</i>\n\n"
        notification_text += f"🔗 <b>Ссылка на пост:</b>\n"
        notification_text += f"<a href=\"{post_link}\">Открыть пост в канале</a>\n\n"
        notification_text += f"⏰ <b>Время публикации:</b> {datetime.datetime.now(timezone(timedelta(hours=3))).strftime('%d.%m.%Y в %H:%M')}\n\n"
        notification_text += f"💰 <b>Награда:</b> После проверки вы получите токены за пост!"
        
        # Отправляем уведомление
        await bot.send_message(
            chat_id=author_id,
            text=notification_text,
            parse_mode="HTML",
            disable_web_page_preview=True
        )
        print(f"[send_publication_notification] Notification sent to user {author_id}")
        
    except Exception as e:
        print(f"[send_publication_notification] Error sending notification: {e}")


async def send_publication_and_payment_notification(bot: Bot, post: dict, channel_message_id: int, tokens_added: int, new_balance: str):
    """Отправляет объединенное уведомление о публикации и оплате"""
    try:
        author_id = post.get('author')
        if not author_id:
            print(f"[send_publication_and_payment_notification] No author_id in post {post.get('id')}")
            return
        
        # Формируем ссылку на пост в канале
        channel_id = os.getenv("CHANNEL_ID")
        if not channel_id:
            print(f"[send_publication_and_payment_notification] CHANNEL_ID not set")
            return
            
        if channel_id.startswith('-100'):
            channel_id = channel_id[4:]  # Убираем префикс -100 для ссылки
        
        post_link = f"https://t.me/c/{channel_id}/{channel_message_id}"
        
        # Формируем объединенное сообщение
        notification_text = f"🎉 <b>Ваш пост опубликован и оплачен!</b>\n\n"
        notification_text += f"📝 <b>Содержание:</b>\n"
        notification_text += f"<i>{post.get('content', '')[:100]}{'...' if len(post.get('content', '')) > 100 else ''}</i>\n\n"
        notification_text += f"🔗 <b>Ссылка на пост:</b>\n"
        notification_text += f"<a href=\"{post_link}\">Открыть пост в канале</a>\n\n"
        notification_text += f"💰 <b>Награда:</b>\n"
        notification_text += f"➕ <b>Получено токенов:</b> +{tokens_added}\n"
        notification_text += f"📊 <b>Новый баланс:</b> {new_balance} т.\n\n"
        notification_text += f"⏰ <b>Время публикации:</b> {datetime.datetime.now(timezone(timedelta(hours=3))).strftime('%d.%m.%Y в %H:%M')}\n\n"
        notification_text += f"🎉 <b>Спасибо за качественный контент!</b>\n"
        notification_text += f"💡 <b>Совет:</b> Используйте токены для покупки псевдонимов в магазине /market"
        
        # Отправляем уведомление
        await bot.send_message(
            chat_id=author_id,
            text=notification_text,
            parse_mode="HTML",
            disable_web_page_preview=True
        )
        print(f"[send_publication_and_payment_notification] Combined notification sent to user {author_id}")
        
    except Exception as e:
        print(f"[send_publication_and_payment_notification] Error sending combined notification: {e}")


async def publish_to_channel(post, bot) -> tuple[bool, int]:
    """Публикует пост в Telegram-канал и возвращает ID сообщения в канале"""
    try:
        fci = os.getenv("OFFERS_CHAT_ID")
        mi = post["telegram_id"]
        ci = os.getenv("CHANNEL_ID")
        print(f"Publishing post: from_chat_id={fci}, message_id={mi}, chat_id={ci}")
        
        # Копируем сообщение в канал и получаем ID нового сообщения
        channel_message = await bot.copy_message(
            from_chat_id=os.getenv("OFFERS_CHAT_ID"),
            message_id=post["telegram_id"],
            chat_id=os.getenv("CHANNEL_ID")
        )
        
        print(f"Post published successfully! Channel message ID: {channel_message.message_id}")
        print(f"Channel message object type: {type(channel_message)}")
        print(f"Channel message ID: {channel_message.message_id}")
        
        return True, channel_message.message_id
    except Exception as e:
        print(f"Ошибка публикации: {e}")
        return False, 0


async def mark_as_posted(post_id: int) -> None:
    """Помечает пост как опубликованный в БД (заглушка)"""
    await mark_post_as_posted(post_id)
    print(f"Помечаю пост {post_id} как опубликованный")

async def post_checker(bot):
    """Основной цикл проверки постов"""
    print(f"Starting post checker...")
    print(f"OFFERS_CHAT_ID: {os.getenv('OFFERS_CHAT_ID')}")
    print(f"CHANNEL_ID: {os.getenv('CHANNEL_ID')}")
    
    # Счетчик для пересчета очереди (каждые 10 циклов = 200 секунд)
    queue_recalc_counter = 0
    
    while True:
        try:
            # Пересчитываем очередь в начале каждого цикла для максимальной актуальности
            print(f"[post_checker] Performing queue recalculation at cycle start...")
            try:
                recalc_result = await recalculate_queue_after_immediate_publication()
                if 'error' in recalc_result:
                    print(f"[post_checker] Queue recalculation failed: {recalc_result['error']}")
                else:
                    updated_count = int(recalc_result.get('updated_count', 0))
                    if updated_count > 0:
                        print(f"[post_checker] Queue recalculated at cycle start: {updated_count} posts updated")
                    else:
                        print(f"[post_checker] Queue recalculation at cycle start completed: no posts to update")
            except Exception as e:
                print(f"[post_checker] Exception during queue recalculation at cycle start: {e}")
            
            # Создаем текущее время с часовым поясом UTC
            now = datetime.datetime.now(datetime.timezone.utc)
            posts_response = await get_recent_posts()
            
            # Проверяем, что получили корректный ответ от API
            if 'error' in posts_response:
                print(f"Error getting posts: {posts_response['error']}")
                await asyncio.sleep(20)
                continue
            
            # Извлекаем список постов из ответа API
            posts = posts_response.get('results', []) if isinstance(posts_response, dict) else posts_response
            
            # Пересчитываем очередь каждые 10 циклов (200 секунд) - дополнительная проверка
            queue_recalc_counter += 1
            if queue_recalc_counter >= 10:
                print(f"[post_checker] Performing periodic queue recalculation...")
                try:
                    recalc_result = await recalculate_queue_after_immediate_publication()
                    if 'error' in recalc_result:
                        print(f"[post_checker] Periodic queue recalculation failed: {recalc_result['error']}")
                    else:
                        updated_count = int(recalc_result.get('updated_count', 0))
                        if updated_count > 0:
                            print(f"[post_checker] Periodic queue recalculated: {updated_count} posts updated")
                        else:
                            print(f"[post_checker] Periodic queue recalculation completed: no posts to update")
                except Exception as e:
                    print(f"[post_checker] Exception during periodic queue recalculation: {e}")
                
                queue_recalc_counter = 0  # Сбрасываем счетчик
            
            for post in posts:
                if post.get('is_posted', False):
                    continue
                    
                posted_at = datetime.datetime.fromisoformat(post['posted_at'])
                # Если время из БД без пояса - добавляем UTC
                if posted_at.tzinfo is None:
                    posted_at = posted_at.replace(tzinfo=datetime.timezone.utc)
                # Если с поясом - конвертируем в UTC
                else:
                    posted_at = posted_at.astimezone(datetime.timezone.utc)
                
                time_diff = (now - posted_at).total_seconds()
                print(f"Post {post['id']} (telegram_id={post['telegram_id']}): scheduled={posted_at}, now={now}, time_diff={time_diff}")
                
                # Проверяем, что текущее время больше или равно запланированному времени
                # И что разница не превышает 60 часов (для тестов)
                # Также публикуем посты, которые были созданы более 30 минут назад, даже если время публикации в будущем
                should_publish = False
                
                if time_diff >= 0 and time_diff < 60 * 60 * 60:
                    # Обычная проверка - время публикации наступило
                    should_publish = True
                    print(f"Post {post['id']} scheduled time has arrived")
                elif time_diff < 0:
                    # Время публикации в будущем, но проверяем, не был ли пост создан давно
                    # Получаем время создания поста (если есть) или используем текущее время
                    post_created_time = post.get('created_at') or post.get('posted_at')
                    if post_created_time:
                        try:
                            created_at = datetime.datetime.fromisoformat(post_created_time)
                            if created_at.tzinfo is None:
                                created_at = created_at.replace(tzinfo=datetime.timezone.utc)
                            else:
                                created_at = created_at.astimezone(datetime.timezone.utc)
                            
                            time_since_creation = (now - created_at).total_seconds() / 60  # в минутах
                            if time_since_creation >= 30:  # Пост создан более 30 минут назад
                                should_publish = True
                                print(f"Post {post['id']} created {time_since_creation:.1f} minutes ago, publishing despite future schedule")
                        except Exception as e:
                            print(f"Error parsing post creation time for post {post['id']}: {e}")
                
                if should_publish:
                    print(f"Publishing post {post['id']} to channel...")
                    success, channel_message_id = await publish_to_channel(post, bot)
                    if success:
                        print(f"Updating post {post['id']} with channel_message_id={channel_message_id}")
                        # Сохраняем ID сообщения в канале
                        update_result = await update_post_channel_info(post['id'], channel_message_id)
                        print(f"Update result: {update_result}")
                        await mark_as_posted(post['id'])
                        print(f"Post {post['id']} marked as posted")
                        
                        # Обрабатываем оплату и отправляем объединенное уведомление
                        payment_result = await process_post_payment(post['id'])
                        if 'error' not in payment_result:
                            tokens_added = payment_result.get('tokens_added', 0)
                            author_balance = payment_result.get('author_balance', 'N/A')
                            await send_publication_and_payment_notification(bot, post, channel_message_id, tokens_added, author_balance)
                        else:
                            print(f"Error processing payment for post {post['id']}: {payment_result['error']}")
                            # Отправляем только уведомление о публикации если оплата не прошла
                            await send_publication_notification(bot, post, channel_message_id)
                        
                        # Пересчитываем очередь после публикации поста
                        print(f"[post_checker] Recalculating queue after post publication...")
                        try:
                            recalc_result = await recalculate_queue_after_immediate_publication()
                            if 'error' in recalc_result:
                                print(f"[post_checker] Queue recalculation after publication failed: {recalc_result['error']}")
                            else:
                                updated_count = int(recalc_result.get('updated_count', 0))
                                print(f"[post_checker] Queue recalculated after publication: {updated_count} posts updated")
                        except Exception as e:
                            print(f"[post_checker] Exception during queue recalculation after publication: {e}")
                    else:
                        print(f"Failed to publish post {post['id']}")
                else:
                    print(f"Post {post['id']} scheduled for future: {abs(time_diff)} seconds remaining")
        
        except Exception as e:
            print(f"Ошибка в цикле проверки: {e}")
            import traceback
            traceback.print_exc()
        
        await asyncio.sleep(20)