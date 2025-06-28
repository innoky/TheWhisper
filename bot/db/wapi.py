import aiohttp
import logging
import asyncio
import json
from datetime import datetime, timezone, timedelta
from typing import Union
import os

API_BASE = 'http://backend:8000/api/'

async def try_create_user(user_id, username, firstname, lastname) -> dict:
    """
    Проверяет существование пользователя по ID и если его не существует, то создает его
    
    Возвращает:
        dict: Ответ сервера в формате JSON или словарь с ошибкой
    """
    headers = {'Content-Type': 'application/json'}
    payload = {
        "id": user_id,
        "username": username,
        "firstname": firstname or "N/A",
        "lastname": lastname or "N/A",
        "balance": 100.50,
        "level": 1
    }
    API_URL = API_BASE + 'users/'
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(API_URL, json=payload, headers=headers) as response:
                return await response.json()
    except Exception as e:
        logging.exception("Error in create_or_skip_user")
        return {"error": f"Request failed: {str(e)}"}

async def get_last_post() -> dict:
    """
    Получает информацию о последнем посте через API
    
    Возвращает:
        dict: Данные последнего поста или словарь с ошибкой
    """
    headers = {'Accept': 'application/json'}
    API_URL = API_BASE + 'posts/?is_rejected=false&ordering=-posted_at&page=1&page_size=1'
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(API_URL, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    logging.info(f"[get_last_post] Raw response type: {type(data)}")
                    
                    # Обрабатываем разные форматы ответа
                    if isinstance(data, list) and len(data) > 0:
                        logging.info(f"[get_last_post] API returned list, returning first post")
                        return data[0]
                    elif isinstance(data, dict) and 'results' in data and data['results']:
                        logging.info(f"[get_last_post] API returned dict with 'results' key, returning first post")
                        return data['results'][0]
                    else:
                        logging.warning(f"[get_last_post] No posts found or unexpected format")
                    return {}
                else:
                    error_text = await response.text()
                    logging.error(f"[get_last_post] API error {response.status}: {error_text}")
                    return {"error": f"API request failed with status {response.status}", "details": error_text}
    except Exception as e:
        logging.exception("Error in get_last_post")
        return {"error": f"Request failed: {str(e)}"}
    
def format_posted_at(dt):
    # dt — это datetime с tzinfo
    # DRF ожидает: 2025-06-27T22:46:54+0300
    return dt.strftime('%Y-%m-%dT%H:%M:%S%z')

async def try_create_post(author_id, content, post_time, telegram_id) -> dict:
    """
    Создает новый пост с указанным временем публикации.
    
    Args:
        post_time: datetime объект или строка в ISO формате.
    """
    headers = {'Content-Type': 'application/json'}
    if isinstance(post_time, datetime):
        post_time_str = format_posted_at(post_time)
    else:
        post_time_str = post_time  # если вдруг строка уже
    payload = {
        "author": author_id,
        "content": content,
        "posted_at": post_time_str,
        "telegram_id": telegram_id,
        "is_posted": False,
        "is_rejected": False
    }
    API_URL = API_BASE + 'posts/'
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(API_URL, json=payload, headers=headers) as response:
                if response.status >= 400:
                    text = await response.text()
                    logging.error(f"[try_create_post] API error {response.status}: {text}")
                return await response.json()
    except Exception as e:
        logging.exception("Error in try_create_post")
        return {"error": f"Request failed: {str(e)}"}
    
async def get_recent_posts() -> dict:
    """
    Получает информацию о последних 50 постах через API
    
    Возвращает:
        dict: Данные последних постов или словарь с ошибкой
    """
    headers = {'Accept': 'application/json'}
    API_URL = API_BASE + 'posts/?is_rejected=false&ordering=-posted_at&page=1&page_size=50'
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(API_URL, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    logging.info(f"[get_recent_posts] Raw response type: {type(data)}")
                    logging.info(f"[get_recent_posts] Raw response: {str(data)[:200]}...")
                    
                    # Обрабатываем разные форматы ответа
                    if isinstance(data, list):
                        logging.info(f"[get_recent_posts] API returned list with {len(data)} posts")
                        return {"results": data}
                    elif isinstance(data, dict):
                        if 'results' in data:
                            logging.info(f"[get_recent_posts] API returned dict with 'results' key, {len(data['results'])} posts")
                            return data
                        else:
                            logging.warning(f"[get_recent_posts] API returned dict without 'results' key: {list(data.keys())}")
                            return {"results": []}
                    else:
                        logging.warning(f"[get_recent_posts] Unexpected data format: {type(data)}")
                        return {"results": []}
                else:
                    error_text = await response.text()
                    logging.error(f"[get_recent_posts] API error {response.status}: {error_text}")
                    return {"error": f"API request failed with status {response.status}", "details": error_text}
    except Exception as e:
        logging.exception("Error in get_recent_posts")
        return {"error": f"Request failed: {str(e)}"}

async def mark_post_as_posted(post_id):
    headers = {'Content-Type': 'application/json'}
    API_URL = API_BASE + f'posts/{post_id}/mark_as_posted/'
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(API_URL, headers=headers) as response:
                return await response.json()
    except Exception as e:
        logging.exception("Error in mark_post_as_posted")
        return {"error": f"Request failed: {str(e)}"}

async def mark_post_as_rejected(post_id):
    headers = {'Content-Type': 'application/json'}
    API_URL = API_BASE + f'posts/{post_id}/mark_as_rejected/'
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(API_URL, headers=headers) as response:
                return await response.json()
    except Exception as e:
        logging.exception("Error in mark_post_as_rejected")
        return {"error": f"Request failed: {str(e)}"}

async def mark_post_as_rejected_by_telegram_id(telegram_id: int):
    """
    Отклоняет пост по telegram_id.
    """
    # Сначала получаем пост по telegram_id
    post_info = await get_post_by_telegram_id(telegram_id)
    if 'error' in post_info:
        return post_info
    
    # Затем отклоняем пост по его id
    return await mark_post_as_rejected(post_info['id'])

async def leave_anon_comment(telegram_id, reply_to, user_id, content):
    """
    Создает новый анонимный комментарий.
    """
    headers = {'Content-Type': 'application/json'}
    payload = {
        "reply_to": reply_to,
        "author": user_id,
        "content": content,
        "telegram_id": telegram_id
    }
    API_URL = API_BASE + 'comments/'
    
    logging.info(f"[leave_anon_comment] Creating comment with payload: {payload}")
    logging.info(f"[leave_anon_comment] API URL: {API_URL}")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(API_URL, json=payload, headers=headers) as response:
                logging.info(f"[leave_anon_comment] Response status: {response.status}")
                result = await response.json()
                logging.info(f"[leave_anon_comment] Response: {result}")
                return result
    except Exception as e:
        logging.exception("Error in leave_anon_comment")
        return {"error": f"Request failed: {str(e)}"}

async def get_user_pseudo_names(user_id):
    headers = {'Accept': 'application/json'}
    API_URL = API_BASE + f'users/{user_id}/pseudo_names/'
    logging.info(f"[get_user_pseudo_names] Requesting URL: {API_URL}")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(API_URL, headers=headers) as response:
                logging.info(f"[get_user_pseudo_names] Response status: {response.status}")
                logging.info(f"[get_user_pseudo_names] Response headers: {dict(response.headers)}")
                
                if response.status == 200:
                    data = await response.json()
                    logging.info(f"[get_user_pseudo_names] Raw data: {data}")
                    logging.info(f"[get_user_pseudo_names] Data type: {type(data)}")
                    
                    # Проверяем, есть ли пагинация
                    if isinstance(data, dict) and 'results' in data:
                        results = data['results']
                        logging.info(f"[get_user_pseudo_names] Found pagination, results: {results}")
                    elif isinstance(data, list):
                        results = data
                        logging.info(f"[get_user_pseudo_names] Direct list response: {results}")
                    else:
                        logging.error(f"[get_user_pseudo_names] Unexpected data format: {type(data)}")
                        return []
                    
                    logging.info(f"[get_user_pseudo_names] Results length: {len(results)}")
                    
                    pseudo_ids = []
                    for i, item in enumerate(results):
                        logging.info(f"[get_user_pseudo_names] Processing item {i}: {item} (type: {type(item)})")
                        if isinstance(item, dict) and 'pseudo_name' in item:
                            pseudo_name = item['pseudo_name']
                            if isinstance(pseudo_name, dict) and 'id' in pseudo_name:
                                pseudo_ids.append(pseudo_name['id'])
                                logging.info(f"[get_user_pseudo_names] Added ID from dict: {pseudo_name['id']}")
                            elif isinstance(pseudo_name, int):
                                pseudo_ids.append(pseudo_name)
                                logging.info(f"[get_user_pseudo_names] Added ID from int: {pseudo_name}")
                            else:
                                logging.warning(f"[get_user_pseudo_names] Unknown pseudo_name format: {pseudo_name}")
                        elif isinstance(item, int):
                            pseudo_ids.append(item)
                            logging.info(f"[get_user_pseudo_names] Added ID from int: {item}")
                        else:
                            logging.warning(f"[get_user_pseudo_names] Unknown item format: {item}")
                    
                    logging.info(f"[get_user_pseudo_names] Final extracted pseudo_ids: {pseudo_ids}")
                    return pseudo_ids
                elif response.status == 404:
                    logging.warning(f"[get_user_pseudo_names] User {user_id} has no pseudo names endpoint")
                    return []
                else:
                    error_text = await response.text()
                    logging.error(f"[get_user_pseudo_names] API error {response.status}: {error_text}")
                    return []
    except Exception as e:
        logging.warning(f"[get_user_pseudo_names] Error for user {user_id}: {e}")
        return []

async def get_user_pseudo_names_full(user_id):
    """
    Возвращает полную информацию о купленных никах пользователя (ID и название)
    """
    headers = {'Accept': 'application/json'}
    API_URL = API_BASE + f'users/{user_id}/pseudo_names/'
    logging.info(f"[get_user_pseudo_names_full] Requesting URL: {API_URL}")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(API_URL, headers=headers) as response:
                logging.info(f"[get_user_pseudo_names_full] Response status: {response.status}")
                logging.info(f"[get_user_pseudo_names_full] Response headers: {dict(response.headers)}")
                
                if response.status == 200:
                    data = await response.json()
                    logging.info(f"[get_user_pseudo_names_full] Raw data: {data}")
                    logging.info(f"[get_user_pseudo_names_full] Data type: {type(data)}")
                    
                    # Проверяем, есть ли пагинация
                    if isinstance(data, dict) and 'results' in data:
                        results = data['results']
                        logging.info(f"[get_user_pseudo_names_full] Found pagination, results: {results}")
                    elif isinstance(data, list):
                        results = data
                        logging.info(f"[get_user_pseudo_names_full] Direct list response: {results}")
                    else:
                        logging.error(f"[get_user_pseudo_names_full] Unexpected data format: {type(data)}")
                        return []
                    
                    logging.info(f"[get_user_pseudo_names_full] Results length: {len(results)}")
                    
                    pseudo_names = []
                    for i, item in enumerate(results):
                        logging.info(f"[get_user_pseudo_names_full] Processing item {i}: {item} (type: {type(item)})")
                        if isinstance(item, dict) and 'pseudo_name' in item:
                            pseudo_name = item['pseudo_name']
                            if isinstance(pseudo_name, dict) and 'id' in pseudo_name and 'pseudo' in pseudo_name:
                                pseudo_names.append((pseudo_name['id'], pseudo_name['pseudo']))
                                logging.info(f"[get_user_pseudo_names_full] Added from dict: ({pseudo_name['id']}, {pseudo_name['pseudo']})")
                            elif isinstance(pseudo_name, int):
                                # Получаем полную информацию о нике по ID
                                full_info = await get_pseudo_name_by_id(pseudo_name)
                                if full_info and isinstance(full_info, dict) and 'pseudo' in full_info:
                                    pseudo_names.append((pseudo_name, full_info['pseudo']))
                                    logging.info(f"[get_user_pseudo_names_full] Added from API: ({pseudo_name}, {full_info['pseudo']})")
                                else:
                                    # Если не удалось получить информацию, используем заглушку
                                    pseudo_names.append((pseudo_name, f"Nick_{pseudo_name}"))
                                    logging.warning(f"[get_user_pseudo_names_full] Failed to get info for {pseudo_name}, using placeholder")
                            else:
                                logging.warning(f"[get_user_pseudo_names_full] Unknown pseudo_name format: {pseudo_name}")
                        elif isinstance(item, int):
                            # Получаем полную информацию о нике по ID
                            full_info = await get_pseudo_name_by_id(item)
                            if full_info and isinstance(full_info, dict) and 'pseudo' in full_info:
                                pseudo_names.append((item, full_info['pseudo']))
                                logging.info(f"[get_user_pseudo_names_full] Added from API: ({item}, {full_info['pseudo']})")
                            else:
                                # Если не удалось получить информацию, используем заглушку
                                pseudo_names.append((item, f"Nick_{item}"))
                                logging.warning(f"[get_user_pseudo_names_full] Failed to get info for {item}, using placeholder")
                        else:
                            logging.warning(f"[get_user_pseudo_names_full] Unknown item format: {item}")
                    
                    logging.info(f"[get_user_pseudo_names_full] Final extracted pseudo_names: {pseudo_names}")
                    return pseudo_names
                elif response.status == 404:
                    logging.warning(f"[get_user_pseudo_names_full] User {user_id} has no pseudo names endpoint")
                    return []
                else:
                    error_text = await response.text()
                    logging.error(f"[get_user_pseudo_names_full] API error {response.status}: {error_text}")
                    return []
    except Exception as e:
        logging.warning(f"[get_user_pseudo_names_full] Error for user {user_id}: {e}")
        return []

async def get_pseudo_name_by_id(pseudo_id):
    """
    Получает полную информацию о нике по его ID
    """
    headers = {'Accept': 'application/json'}
    API_URL = API_BASE + f'pseudo-names/{pseudo_id}/'
    logging.info(f"[get_pseudo_name_by_id] Requesting URL: {API_URL}")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(API_URL, headers=headers) as response:
                logging.info(f"[get_pseudo_name_by_id] Response status: {response.status}")
                
                if response.status == 200:
                    result = await response.json()
                    logging.info(f"[get_pseudo_name_by_id] Result: {result}")
                    return result
                else:
                    error_text = await response.text()
                    logging.error(f"[get_pseudo_name_by_id] API error {response.status}: {error_text}")
                    return None
    except Exception as e:
        logging.warning(f"[get_pseudo_name_by_id] Error for pseudo_id {pseudo_id}: {e}")
        return None

async def is_user_banned(user_id):
    headers = {'Accept': 'application/json'}
    API_URL = API_BASE + f'users/{user_id}/'
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(API_URL, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get('is_banned', False)
                else:
                    return {"error": f"API request failed with status {response.status}", "details": await response.text()}
    except Exception as e:
        logging.exception("Error in is_user_banned")
        return {"error": f"Request failed: {str(e)}"}

async def ban_user(user_id):
    headers = {'Content-Type': 'application/json'}
    API_URL = API_BASE + f'users/{user_id}/ban/'
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(API_URL, headers=headers) as response:
                return await response.json()
    except Exception as e:
        logging.exception("Error in ban_user")
        return {"error": f"Request failed: {str(e)}"}

async def unban_user(user_id):
    # Бан/разбан реализован одним и тем же endpoint
    return await ban_user(user_id)

async def add_pseudo_name(pseudo: str, price: float, is_available: bool = True) -> dict:
    """
    Добавляет новый псевдоним в базу данных.
    """
    headers = {'Content-Type': 'application/json'}
    payload = {
        "pseudo": pseudo,
        "price": price,
        "is_available": is_available
    }
    API_URL = API_BASE + 'pseudo-names/'
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(API_URL, json=payload, headers=headers) as response:
                return await response.json()
    except Exception as e:
        logging.exception("Error in add_pseudo_name")
        return {"error": f"Request failed: {str(e)}"}

async def add_balance(user_id: int, amount: float) -> dict:
    """
    Добавляет указанную сумму к балансу пользователя.
    """
    headers = {'Content-Type': 'application/json'}
    payload = {
        "amount": amount
    }
    API_URL = API_BASE + f'users/{user_id}/addbalance/'
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(API_URL, json=payload, headers=headers) as response:
                return await response.json()
    except Exception as e:
        logging.exception("Error in add_balance")
        return {"error": f"Request failed: {str(e)}"}

async def set_balance(user_id: int, amount: float) -> dict:
    """
    Устанавливает баланс пользователя на указанную сумму.
    """
    headers = {'Content-Type': 'application/json'}
    payload = {
        "amount": amount
    }
    API_URL = API_BASE + f'users/{user_id}/setbalance/'
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(API_URL, json=payload, headers=headers) as response:
                return await response.json()
    except Exception as e:
        logging.exception("Error in set_balance")
        return {"error": f"Request failed: {str(e)}"}

async def get_all_pseudo_names() -> Union[list, dict]:
    """
    Получает список всех доступных псевдонимов.
    """
    headers = {'Accept': 'application/json'}
    API_URL = API_BASE + 'pseudo-names/'
    logging.info(f"[get_all_pseudo_names] Requesting URL: {API_URL}")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(API_URL, headers=headers) as response:
                logging.info(f"[get_all_pseudo_names] Response status: {response.status}")
                logging.info(f"[get_all_pseudo_names] Response headers: {dict(response.headers)}")
                
                if response.status == 200:
                    # Проверяем content-type
                    content_type = response.headers.get('content-type', '')
                    logging.info(f"[get_all_pseudo_names] Content-Type: {content_type}")
                    
                    if 'application/json' in content_type:
                        data = await response.json()
                        logging.info(f"[get_all_pseudo_names] Success with endpoint pseudo-names/")
                        logging.info(f"[get_all_pseudo_names] Response type: {type(data)}")
                        logging.info(f"[get_all_pseudo_names] Response: {str(data)[:200]}...")
                        
                        # Проверяем, что получили список или объект с results
                        if isinstance(data, list):
                            return data
                        elif isinstance(data, dict) and 'results' in data:
                            return data['results']
                        else:
                            logging.error(f"[get_all_pseudo_names] Unexpected response format: {type(data)}")
                            return {"error": f"Unexpected response format: {type(data)}"}
                    else:
                        # Получаем текст ответа для отладки
                        text_response = await response.text()
                        logging.error(f"[get_all_pseudo_names] Non-JSON response: {text_response[:500]}...")
                        return {"error": f"Non-JSON response: {content_type}"}
                else:
                    error_text = await response.text()
                    logging.error(f"[get_all_pseudo_names] API error {response.status}: {error_text}")
                    return {"error": f"API request failed with status {response.status}", "details": error_text}
    except Exception as e:
        logging.exception("Error in get_all_pseudo_names")
        return {"error": f"Request failed: {str(e)}"}

async def deactivate_pseudo_name(pseudo_id: int) -> dict:
    """
    Деактивирует псевдоним (делает его недоступным для покупки).
    """
    headers = {'Content-Type': 'application/json'}
    API_URL = API_BASE + f'pseudo-names/{pseudo_id}/'
    try:
        async with aiohttp.ClientSession() as session:
            async with session.patch(API_URL, json={"is_available": False}, headers=headers) as response:
                return await response.json()
    except Exception as e:
        logging.exception("Error in deactivate_pseudo_name")
        return {"error": f"Request failed: {str(e)}"}

async def purchase_pseudo_name(user_id: int, pseudo_id: int) -> dict:
    """
    Покупает псевдоним для пользователя.
    """
    headers = {'Content-Type': 'application/json'}
    payload = {
        "user": user_id,
        "pseudo_name": pseudo_id
    }
    API_URL = API_BASE + 'user-pseudo-names/'
    
    logging.info(f"[purchase_pseudo_name] Requesting URL: {API_URL}")
    logging.info(f"[purchase_pseudo_name] Payload: {payload}")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(API_URL, json=payload, headers=headers) as response:
                logging.info(f"[purchase_pseudo_name] Response status: {response.status}")
                
                if response.status == 200 or response.status == 201:
                    data = await response.json()
                    logging.info(f"[purchase_pseudo_name] Success: {data}")
                    return data
                else:
                    error_text = await response.text()
                    logging.error(f"[purchase_pseudo_name] API error {response.status}: {error_text}")
                    return {"error": f"API request failed with status {response.status}", "details": error_text}
    except Exception as e:
        logging.exception("Error in purchase_pseudo_name")
        return {"error": f"Request failed: {str(e)}"}

async def get_user_info(user_id):
    """
    Получает информацию о пользователе.
    """
    headers = {'Accept': 'application/json'}
    API_URL = API_BASE + f'users/{user_id}/'
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(API_URL, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {"error": f"API request failed with status {response.status}", "details": await response.text()}
    except Exception as e:
        logging.exception("Error in get_user_info")
        return {"error": f"Request failed: {str(e)}"}

async def update_user_info(user_id, username, firstname, lastname) -> dict:
    """
    Обновляет информацию о пользователе.
    """
    headers = {'Content-Type': 'application/json'}
    payload = {
        "username": username,
        "firstname": firstname,
        "lastname": lastname
    }
    API_URL = API_BASE + f'users/{user_id}/'
    try:
        async with aiohttp.ClientSession() as session:
            async with session.patch(API_URL, json=payload, headers=headers) as response:
                return await response.json()
    except Exception as e:
        logging.exception("Error in update_user_info")
        return {"error": f"Request failed: {str(e)}"}

async def update_post_channel_info(post_id: int, channel_message_id: int) -> dict:
    """
    Обновляет информацию о посте в канале (ID сообщения в канале и время публикации).
    """
    headers = {'Content-Type': 'application/json'}
    current_time = datetime.now(timezone(timedelta(hours=3)))
    formatted_time = current_time.strftime('%Y-%m-%dT%H:%M:%S%z')
    
    payload = {
        "channel_message_id": channel_message_id,
        "channel_posted_at": formatted_time
    }
    API_URL = API_BASE + f'posts/{post_id}/'
    try:
        async with aiohttp.ClientSession() as session:
            async with session.patch(API_URL, json=payload, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    logging.info(f"[update_post_channel_info] Successfully updated post {post_id} with channel_message_id={channel_message_id}")
                    return result
                else:
                    error_text = await response.text()
                    logging.error(f"[update_post_channel_info] API error {response.status}: {error_text}")
                    return {"error": f"API request failed with status {response.status}", "details": error_text}
    except Exception as e:
        logging.exception(f"[update_post_channel_info] Exception for post_id={post_id}")
        return {"error": f"Request failed: {str(e)}"}

async def get_post_info(post_id: int) -> dict:
    """
    Получает информацию о посте по ID.
    """
    headers = {'Accept': 'application/json'}
    API_URL = API_BASE + f'posts/{post_id}/'
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(API_URL, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {"error": f"API request failed with status {response.status}", "details": await response.text()}
    except Exception as e:
        logging.exception("Error in get_post_info")
        return {"error": f"Request failed: {str(e)}"}

async def get_post_by_telegram_id(telegram_id: int) -> dict:
    """
    Получает информацию о посте по telegram_id.
    """
    headers = {'Accept': 'application/json'}
    API_URL = API_BASE + f'posts/?telegram_id={telegram_id}'
    logging.info(f"[get_post_by_telegram_id] Searching for telegram_id={telegram_id}, URL={API_URL}")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(API_URL, headers=headers) as response:
                logging.info(f"[get_post_by_telegram_id] Response status: {response.status}")
                if response.status == 200:
                    data = await response.json()
                    logging.info(f"[get_post_by_telegram_id] Response data: {data}")
                    
                    # Проверяем разные форматы ответа
                    results = None
                    if isinstance(data, list):
                        # Если ответ - список (без пагинации)
                        results = data
                    elif isinstance(data, dict) and 'results' in data:
                        # Если ответ - объект с ключом results (с пагинацией)
                        results = data['results']
                    
                    if results and len(results) > 0:
                        logging.info(f"[get_post_by_telegram_id] Found post: {results[0]}")
                        return results[0]  # Возвращаем первый найденный пост
                    else:
                        logging.warning(f"[get_post_by_telegram_id] No posts found for telegram_id={telegram_id}")
                        return {"error": "Post not found"}
                else:
                    error_text = await response.text()
                    logging.error(f"[get_post_by_telegram_id] API error {response.status}: {error_text}")
                    return {"error": f"API request failed with status {response.status}", "details": error_text}
    except Exception as e:
        logging.exception(f"[get_post_by_telegram_id] Exception for telegram_id={telegram_id}")
        return {"error": f"Request failed: {str(e)}"}

async def process_post_payment(post_id: int) -> dict:
    """
    Обрабатывает оплату поста на основе уровня автора.
    """
    headers = {'Content-Type': 'application/json'}
    API_URL = API_BASE + f'posts/{post_id}/process_payment/'
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(API_URL, headers=headers) as response:
                return await response.json()
    except Exception as e:
        logging.exception("Error in process_post_payment")
        return {"error": f"Request failed: {str(e)}"}

async def publish_post_now(post_id: int) -> dict:
    """
    Немедленно публикует пост и обрабатывает оплату.
    """
    headers = {'Content-Type': 'application/json'}
    API_URL = API_BASE + f'posts/{post_id}/publish_now/'
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(API_URL, headers=headers) as response:
                return await response.json()
    except Exception as e:
        logging.exception("Error in publish_post_now")
        return {"error": f"Request failed: {str(e)}"}

async def set_user_level(user_id: int, level: int) -> dict:
    """
    Устанавливает уровень пользователя.
    """
    headers = {'Content-Type': 'application/json'}
    payload = {
        "level": level
    }
    API_URL = API_BASE + f'users/{user_id}/setlevel/'
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(API_URL, json=payload, headers=headers) as response:
                return await response.json()
    except Exception as e:
        logging.exception("Error in set_user_level")
        return {"error": f"Request failed: {str(e)}"}

async def get_active_posts_count() -> int:
    """
    Получает количество активных постов в очереди (не отклоненных и не опубликованных)
    
    Возвращает:
        int: Количество активных постов
    """
    headers = {'Accept': 'application/json'}
    API_URL = API_BASE + 'posts/?is_posted=false&is_rejected=false&page=1&page_size=1000'
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(API_URL, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Обрабатываем разные форматы ответа
                    posts = []
                    if isinstance(data, list):
                        posts = data
                    elif isinstance(data, dict) and 'results' in data:
                        posts = data['results']
                    
                    # Теперь все посты уже отфильтрованы API запросом
                    active_count = len(posts)
                    
                    logging.info(f"[get_active_posts_count] Found {active_count} active posts")
                    return active_count
                else:
                    logging.error(f"[get_active_posts_count] API error {response.status}")
                    return 0
    except Exception as e:
        logging.exception("Error in get_active_posts_count")
        return 0

async def create_user_pseudo_name(user_id: int, pseudo_id: int) -> dict:
    """
    Создает связь между пользователем и псевдонимом (покупает псевдоним)
    """
    headers = {'Content-Type': 'application/json'}
    payload = {
        "user": user_id,
        "pseudo_name": pseudo_id
    }
    API_URL = API_BASE + 'user-pseudo-names/'
    
    logging.info(f"[create_user_pseudo_name] Requesting URL: {API_URL}")
    logging.info(f"[create_user_pseudo_name] Payload: {payload}")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(API_URL, json=payload, headers=headers) as response:
                logging.info(f"[create_user_pseudo_name] Response status: {response.status}")
                
                if response.status == 200 or response.status == 201:
                    data = await response.json()
                    logging.info(f"[create_user_pseudo_name] Success: {data}")
                    return data
                else:
                    error_text = await response.text()
                    logging.error(f"[create_user_pseudo_name] API error {response.status}: {error_text}")
                    return {"error": f"API request failed with status {response.status}", "details": error_text}
    except Exception as e:
        logging.exception("Error in create_user_pseudo_name")
        return {"error": f"Request failed: {str(e)}"}

async def ensure_user_has_default_pseudos(user_id: int) -> bool:
    """
    Убеждается, что у пользователя есть как минимум 3 псевдонима.
    Если нет - создает встроенные псевдонимы.
    """
    logging.info(f"[ensure_user_has_default_pseudos] Checking user {user_id}")
    
    # Получаем текущие псевдонимы пользователя
    user_pseudos = await get_user_pseudo_names(user_id)
    logging.info(f"[ensure_user_has_default_pseudos] User {user_id} has {len(user_pseudos)} pseudos: {user_pseudos}")
    
    if len(user_pseudos) >= 3:
        logging.info(f"[ensure_user_has_default_pseudos] User {user_id} already has enough pseudos")
        return True
    
    # Встроенные псевдонимы по умолчанию
    default_pseudos = [
        {"pseudo": "Потный щитпостер", "price": 0.0},
        {"pseudo": "Секси имошница", "price": 0.0},
        {"pseudo": "Призрак Т-корпуса", "price": 0.0}
    ]
    
    # Получаем все существующие псевдонимы
    all_pseudos = await get_all_pseudo_names()
    if isinstance(all_pseudos, dict) and all_pseudos.get("error"):
        logging.error(f"[ensure_user_has_default_pseudos] Error getting all pseudos: {all_pseudos.get('error')}")
        return False
    
    if not isinstance(all_pseudos, list):
        logging.error(f"[ensure_user_has_default_pseudos] Unexpected all_pseudos format: {type(all_pseudos)}")
        return False
    
    # Проверяем, какие псевдонимы уже существуют
    existing_pseudo_names = [p['pseudo'] for p in all_pseudos]
    logging.info(f"[ensure_user_has_default_pseudos] Existing pseudo names: {existing_pseudo_names}")
    
    # Создаем недостающие псевдонимы
    pseudos_to_create = 3 - len(user_pseudos)
    created_count = 0
    
    for i in range(pseudos_to_create):
        pseudo_data = default_pseudos[i]
        
        # Проверяем, существует ли уже такой псевдоним
        if pseudo_data['pseudo'] in existing_pseudo_names:
            # Находим существующий псевдоним
            existing_pseudo = next(p for p in all_pseudos if p['pseudo'] == pseudo_data['pseudo'])
            pseudo_id = existing_pseudo['id']
            logging.info(f"[ensure_user_has_default_pseudos] Found existing pseudo '{pseudo_data['pseudo']}' with ID {pseudo_id}")
        else:
            # Создаем новый псевдоним в базе данных
            add_result = await add_pseudo_name(
                pseudo=pseudo_data['pseudo'],
                price=pseudo_data['price'],
                is_available=True
            )
            
            if 'id' in add_result:
                pseudo_id = add_result['id']
                logging.info(f"[ensure_user_has_default_pseudos] Created pseudo '{pseudo_data['pseudo']}' with ID {pseudo_id}")
            else:
                logging.error(f"[ensure_user_has_default_pseudos] Failed to create pseudo '{pseudo_data['pseudo']}': {add_result}")
                continue
        
        # Проверяем, не связан ли уже псевдоним с пользователем
        if pseudo_id in user_pseudos:
            logging.info(f"[ensure_user_has_default_pseudos] Pseudo {pseudo_id} already linked to user {user_id}")
            created_count += 1
            continue
        
        # Связываем псевдоним с пользователем
        create_result = await create_user_pseudo_name(user_id, pseudo_id)
        
        if 'id' in create_result and 'pseudo_name' in create_result:
            logging.info(f"[ensure_user_has_default_pseudos] Successfully linked pseudo {pseudo_id} to user {user_id}")
            created_count += 1
        else:
            logging.error(f"[ensure_user_has_default_pseudos] Failed to link pseudo {pseudo_id} to user {user_id}: {create_result}")
    
    logging.info(f"[ensure_user_has_default_pseudos] Created/linked {created_count} pseudos for user {user_id}")
    return created_count > 0

async def purchase_pseudo_name_with_payment(user_id: int, pseudo_id: int) -> dict:
    """
    Покупает псевдоним для пользователя с проверкой баланса и списанием денег.
    """
    logging.info(f"[purchase_pseudo_name_with_payment] User {user_id} trying to purchase pseudo {pseudo_id}")
    
    # Получаем информацию о пользователе
    user_info = await get_user_info(user_id)
    if isinstance(user_info, dict) and user_info.get("error"):
        logging.error(f"[purchase_pseudo_name_with_payment] Error getting user info: {user_info.get('error')}")
        return {"error": "Не удалось получить информацию о пользователе"}
    
    user_balance = float(user_info.get('balance', 0))
    logging.info(f"[purchase_pseudo_name_with_payment] User {user_id} balance: {user_balance}")
    
    # Получаем информацию о псевдониме
    pseudo_info = await get_pseudo_name_by_id(pseudo_id)
    if not pseudo_info or isinstance(pseudo_info, dict) and pseudo_info.get("error"):
        logging.error(f"[purchase_pseudo_name_with_payment] Error getting pseudo info: {pseudo_info}")
        return {"error": "Не удалось получить информацию о псевдониме"}
    
    pseudo_price = float(pseudo_info.get('price', 0))
    logging.info(f"[purchase_pseudo_name_with_payment] Pseudo {pseudo_id} price: {pseudo_price}")
    
    # Проверяем, достаточно ли средств
    if user_balance < pseudo_price:
        logging.warning(f"[purchase_pseudo_name_with_payment] Insufficient balance: {user_balance} < {pseudo_price}")
        return {"error": "Недостаточно средств на балансе"}
    
    # Проверяем, доступен ли псевдоним
    if not pseudo_info.get('is_available', True):
        logging.warning(f"[purchase_pseudo_name_with_payment] Pseudo {pseudo_id} is not available")
        return {"error": "Псевдоним недоступен для покупки"}
    
    # Списываем деньги с баланса
    new_balance = user_balance - pseudo_price
    balance_result = await set_balance(user_id, new_balance)
    if isinstance(balance_result, dict) and balance_result.get("error"):
        logging.error(f"[purchase_pseudo_name_with_payment] Error updating balance: {balance_result.get('error')}")
        return {"error": "Не удалось обновить баланс"}
    
    logging.info(f"[purchase_pseudo_name_with_payment] Updated balance: {user_balance} -> {new_balance}")
    
    # Создаем связь между пользователем и псевдонимом
    purchase_result = await purchase_pseudo_name(user_id, pseudo_id)
    if isinstance(purchase_result, dict) and purchase_result.get("error"):
        logging.error(f"[purchase_pseudo_name_with_payment] Error creating purchase: {purchase_result.get('error')}")
        # Возвращаем деньги, если покупка не удалась
        await set_balance(user_id, user_balance)
        return {"error": "Не удалось создать покупку"}
    
    logging.info(f"[purchase_pseudo_name_with_payment] Successfully purchased pseudo {pseudo_id} for user {user_id}")
    return {
        "success": True,
        "pseudo_name": pseudo_info.get('pseudo'),
        "price": pseudo_price,
        "new_balance": new_balance
    }

async def get_comment_by_telegram_id(telegram_id: int) -> dict:
    """
    Получает информацию о комментарии по его telegram_id
    """
    logging.info(f"[get_comment_by_telegram_id] Starting search for telegram_id: {telegram_id}")
    headers = {'Accept': 'application/json'}
    API_URL = API_BASE + f'comments/telegram/{telegram_id}/'
    logging.info(f"[get_comment_by_telegram_id] Requesting URL: {API_URL}")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(API_URL, headers=headers) as response:
                logging.info(f"[get_comment_by_telegram_id] Response status: {response.status}")
                logging.info(f"[get_comment_by_telegram_id] Response headers: {dict(response.headers)}")
                
                if response.status == 200:
                    result = await response.json()
                    logging.info(f"[get_comment_by_telegram_id] Success! Result: {result}")
                    return result
                elif response.status == 404:
                    logging.warning(f"[get_comment_by_telegram_id] Comment with telegram_id {telegram_id} not found")
                    return {"error": "Comment not found"}
                else:
                    error_text = await response.text()
                    logging.error(f"[get_comment_by_telegram_id] API error {response.status}: {error_text}")
                    return {"error": f"API error {response.status}: {error_text}"}
    except Exception as e:
        logging.exception(f"[get_comment_by_telegram_id] Exception for telegram_id {telegram_id}: {e}")
        return {"error": f"Request failed: {str(e)}"}

async def send_comment_reply_notification(bot, original_comment_author_id: int, original_comment_content: str, reply_telegram_id: int, reply_content: str):
    """
    Отправляет уведомление автору оригинального комментария о том, что на него ответили
    """
    logging.info(f"[send_comment_reply_notification] Starting notification process")
    logging.info(f"[send_comment_reply_notification] original_comment_author_id: {original_comment_author_id}")
    logging.info(f"[send_comment_reply_notification] reply_telegram_id: {reply_telegram_id}")
    logging.info(f"[send_comment_reply_notification] original_comment_content: {original_comment_content[:50]}...")
    logging.info(f"[send_comment_reply_notification] reply_content: {reply_content[:50]}...")
    
    try:
        # Формируем ссылку на ответ - используем CHAT_ID для ссылок
        channel_id = os.getenv("CHAT_ID")
        if not channel_id:
            logging.error(f"[send_comment_reply_notification] CHAT_ID not set")
            return
            
        logging.info(f"[send_comment_reply_notification] CHAT_ID: {channel_id}")
        
        if channel_id.startswith('-100'):
            channel_id = channel_id[4:]  # Убираем префикс -100 для ссылки
            logging.info(f"[send_comment_reply_notification] Removed -100 prefix, channel_id: {channel_id}")
        
        reply_link = f"https://t.me/c/{channel_id}/{reply_telegram_id}"
        logging.info(f"[send_comment_reply_notification] Generated reply_link: {reply_link}")
        
        # Формируем красивое уведомление
        notification_text = f"💬 <b>Вам ответили на комментарий!</b>\n\n"
        notification_text += f"📝 <b>Ваш комментарий:</b>\n"
        notification_text += f"<i>«{original_comment_content[:100]}{'...' if len(original_comment_content) > 100 else ''}»</i>\n\n"
        notification_text += f"💭 <b>Ответ:</b>\n"
        notification_text += f"<i>«{reply_content[:100]}{'...' if len(reply_content) > 100 else ''}»</i>\n\n"
        notification_text += f"🔗 <b>Ссылка на ответ:</b>\n"
        notification_text += f"<a href=\"{reply_link}\">📱 Открыть ответ в канале</a>\n\n"
        notification_text += f"⏰ <b>Время ответа:</b> {datetime.now(timezone(timedelta(hours=3))).strftime('%d.%m.%Y в %H:%M')}\n\n"
        notification_text += f"💡 <b>Хотите ответить?</b>\n"
        notification_text += f"• Перейдите по ссылке выше\n"
        notification_text += f"• Нажмите кнопку 'Ответить' под комментарием"
        
        logging.info(f"[send_comment_reply_notification] Prepared notification text (length: {len(notification_text)})")
        
        # Отправляем уведомление
        logging.info(f"[send_comment_reply_notification] Sending message to user {original_comment_author_id}")
        await bot.send_message(
            chat_id=original_comment_author_id,
            text=notification_text,
            parse_mode="HTML",
            disable_web_page_preview=True
        )
        logging.info(f"[send_comment_reply_notification] Reply notification sent to user {original_comment_author_id}")
        
    except Exception as e:
        logging.error(f"[send_comment_reply_notification] Exception details: {type(e).__name__}: {str(e)}")
        if "chat not found" in str(e).lower():
            logging.warning(f"[send_comment_reply_notification] User {original_comment_author_id} not found or blocked bot")
        else:
            logging.error(f"[send_comment_reply_notification] Error sending reply notification: {e}")
            import traceback
            logging.error(f"[send_comment_reply_notification] Traceback: {traceback.format_exc()}")

async def get_all_users(page_size=1000):
    """
    Получает список всех пользователей (до 1000 за раз).
    """
    headers = {'Accept': 'application/json'}
    API_URL = API_BASE + f'users/?page_size={page_size}'
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(API_URL, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    # Поддержка пагинации и разных форматов
                    if isinstance(data, dict) and 'results' in data:
                        return data['results']
                    elif isinstance(data, list):
                        return data
                    else:
                        return []
                else:
                    return []
    except Exception as e:
        logging.exception("Error in get_all_users")
        return []

async def get_last_published_post_time() -> dict:
    """
    Получает время последнего опубликованного поста.
    Возвращает channel_posted_at последнего опубликованного поста.
    
    Возвращает:
        dict: Данные последнего опубликованного поста или словарь с ошибкой
    """
    headers = {'Accept': 'application/json'}
    # Получаем последний опубликованный пост, отсортированный по channel_posted_at
    API_URL = API_BASE + 'posts/?is_posted=true&ordering=-channel_posted_at&page=1&page_size=1'
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(API_URL, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    if isinstance(data, dict) and 'results' in data and data['results']:
                        post = data['results'][0]
                        return {
                            'id': post.get('id'),
                            'channel_posted_at': post.get('channel_posted_at'),
                            'posted_at': post.get('posted_at'),
                            'author': post.get('author'),
                            'content': post.get('content')
                        }
                    else:
                        return {'error': 'No published posts found'}
                else:
                    return {'error': f'API request failed with status {response.status}'}
    except Exception as e:
        logging.error(f"[get_last_published_post_time] Exception: {e}")
        return {'error': str(e)}

async def recalculate_queue_after_immediate_publication():
    """
    Пересчитывает время для всех постов в очереди после моментальной публикации.
    Вызывается после публикации поста через 'publish_now'.
    """
    headers = {'Accept': 'application/json', 'Content-Type': 'application/json'}
    
    # Получаем все неопубликованные и неотклоненные посты, отсортированные по posted_at
    API_URL = API_BASE + 'posts/?is_posted=false&is_rejected=false&ordering=posted_at'
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(API_URL, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    if isinstance(data, dict) and 'results' in data:
                        queued_posts = data['results']
                    elif isinstance(data, list):
                        queued_posts = data
                    else:
                        queued_posts = []
                    
                    if not queued_posts:
                        logging.info("[recalculate_queue] No posts in queue to recalculate")
                        return {'status': 'success', 'message': 'No posts in queue'}
                    
                    logging.info(f"[recalculate_queue] Found {len(queued_posts)} posts to recalculate")
                    
                    # Получаем время последнего опубликованного поста
                    last_published_data = await get_last_published_post_time()
                    if 'error' in last_published_data:
                        logging.error(f"[recalculate_queue] Error getting last published post: {last_published_data['error']}")
                        return {'error': 'Failed to get last published post'}
                    
                    last_published_time_str = last_published_data.get('channel_posted_at')
                    if not last_published_time_str:
                        logging.error("[recalculate_queue] No channel_posted_at in last published post")
                        return {'error': 'No channel_posted_at in last published post'}
                    
                    # Парсим время последней публикации
                    try:
                        if '+' in last_published_time_str or 'Z' in last_published_time_str:
                            last_published_dt = datetime.strptime(last_published_time_str.replace('Z', '+0000'), "%Y-%m-%dT%H:%M:%S%z")
                        else:
                            last_published_dt = datetime.strptime(last_published_time_str, "%Y-%m-%d %H:%M:%S")
                    except ValueError as e:
                        logging.error(f"[recalculate_queue] Error parsing last published time: {e}")
                        return {'error': f'Error parsing last published time: {e}'}
                    
                    # Пересчитываем время для каждого поста в очереди
                    updated_count = 0
                    current_time = last_published_dt
                    
                    for post in queued_posts:
                        post_id = post.get('id')
                        if not post_id:
                            continue
                        
                        # Добавляем 30 минут к текущему времени
                        current_time = current_time + timedelta(minutes=30)
                        
                        # Форматируем время для API
                        new_post_time = current_time.strftime("%Y-%m-%dT%H:%M:%S%z")
                        
                        # Обновляем время поста
                        update_url = API_BASE + f'posts/{post_id}/'
                        update_data = {'posted_at': new_post_time}
                        
                        try:
                            async with session.patch(update_url, headers=headers, json=update_data) as update_response:
                                if update_response.status == 200:
                                    updated_count += 1
                                    logging.info(f"[recalculate_queue] Updated post {post_id} to {new_post_time}")
                                else:
                                    logging.error(f"[recalculate_queue] Failed to update post {post_id}: {update_response.status}")
                        except Exception as e:
                            logging.error(f"[recalculate_queue] Exception updating post {post_id}: {e}")
                    
                    logging.info(f"[recalculate_queue] Successfully updated {updated_count} posts")
                    return {
                        'status': 'success', 
                        'updated_count': updated_count,
                        'message': f'Updated {updated_count} posts in queue'
                    }
                else:
                    return {'error': f'API request failed with status {response.status}'}
    except Exception as e:
        logging.error(f"[recalculate_queue] Exception: {e}")
        return {'error': str(e)}

async def get_queue_info():
    """
    Получает информацию о всех постах в очереди.
    
    Возвращает:
        dict: Информация о постах в очереди или словарь с ошибкой
    """
    headers = {'Accept': 'application/json'}
    API_URL = API_BASE + 'posts/?is_posted=false&is_rejected=false&ordering=posted_at'
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(API_URL, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    if isinstance(data, dict) and 'results' in data:
                        queued_posts = data['results']
                    elif isinstance(data, list):
                        queued_posts = data
                    else:
                        queued_posts = []
                    
                    return {
                        'status': 'success',
                        'posts': queued_posts,
                        'count': len(queued_posts)
                    }
                else:
                    return {'error': f'API request failed with status {response.status}'}
    except Exception as e:
        logging.error(f"[get_queue_info] Exception: {e}")
        return {'error': str(e)}
