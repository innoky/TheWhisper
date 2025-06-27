import aiohttp
import logging
import asyncio
import json
from datetime import datetime
from typing import Union

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
        "balance": 100.50
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
    API_URL = API_BASE + 'posts/?ordering=-posted_at&page=1&page_size=1'
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(API_URL, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    if 'results' in data and data['results']:
                        return data['results'][0]
                    return {}
                else:
                    return {"error": f"API request failed with status {response.status}", "details": await response.text()}
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
    API_URL = API_BASE + 'posts/?ordering=-posted_at&page=1&page_size=50'
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(API_URL, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {"error": f"API request failed with status {response.status}", "details": await response.text()}
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
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(API_URL, json=payload, headers=headers) as response:
                return await response.json()
    except Exception as e:
        logging.exception("Error in leave_anon_comment")
        return {"error": f"Request failed: {str(e)}"}

async def get_user_pseudo_names(user_id):
    headers = {'Accept': 'application/json'}
    API_URL = API_BASE + f'users/{user_id}/pseudo_names/'
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(API_URL, headers=headers) as response:
                if response.status == 200:
                    results = await response.json()
                    pseudo_ids = []
                    for item in results:
                        if isinstance(item, dict) and 'pseudo_name' in item and isinstance(item['pseudo_name'], dict):
                            pseudo_ids.append(item['pseudo_name']['id'])
                        elif isinstance(item, dict) and 'pseudo_name' in item:
                            pseudo_ids.append(item['pseudo_name'])
                        elif isinstance(item, int):
                            pseudo_ids.append(item)
                    return pseudo_ids
                else:
                    return {"error": f"API request failed with status {response.status}", "details": await response.text()}
    except Exception as e:
        logging.exception("Error in get_user_pseudo_names")
        return {"error": f"Request failed: {str(e)}"}

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
    headers = {'Accept': 'application/json'}
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
                try:
                    return await response.json()
                except aiohttp.ContentTypeError:
                    text = await response.text()
                    logging.error(f"[add_pseudo_name] Non-JSON response: {text}")
                    return {"error": "Non-JSON response from backend", "details": text}
    except Exception as e:
        logging.exception("Error in add_pseudo_name")
        return {"error": f"Request failed: {str(e)}"}

async def add_balance(user_id: int, amount: float) -> dict:
    headers = {'Content-Type': 'application/json'}
    payload = {"amount": amount}
    API_URL = f"{API_BASE}users/{user_id}/addbalance/"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(API_URL, json=payload, headers=headers) as response:
                try:
                    return await response.json()
                except aiohttp.ContentTypeError:
                    text = await response.text()
                    logging.error(f"[add_balance] Non-JSON response: {text}")
                    return {"error": "Non-JSON response from backend", "details": text}
    except Exception as e:
        logging.exception("Error in add_balance")
        return {"error": f"Request failed: {str(e)}"}

async def set_balance(user_id: int, amount: float) -> dict:
    headers = {'Content-Type': 'application/json'}
    payload = {"amount": amount}
    API_URL = f"{API_BASE}users/{user_id}/setbalance/"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(API_URL, json=payload, headers=headers) as response:
                try:
                    return await response.json()
                except aiohttp.ContentTypeError:
                    text = await response.text()
                    logging.error(f"[set_balance] Non-JSON response: {text}")
                    return {"error": "Non-JSON response from backend", "details": text}
    except Exception as e:
        logging.exception("Error in set_balance")
        return {"error": f"Request failed: {str(e)}"}

async def get_all_pseudo_names() -> Union[list, dict]:
    headers = {'Accept': 'application/json'}
    API_URL = API_BASE + 'pseudo-names/'
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(API_URL, headers=headers) as response:
                try:
                    return await response.json()
                except aiohttp.ContentTypeError:
                    text = await response.text()
                    logging.error(f"[get_all_pseudo_names] Non-JSON response: {text}")
                    return {"error": "Non-JSON response from backend", "details": text}
    except Exception as e:
        logging.exception("Error in get_all_pseudo_names")
        return {"error": f"Request failed: {str(e)}"}

async def deactivate_pseudo_name(pseudo_id: int) -> dict:
    headers = {'Content-Type': 'application/json'}
    API_URL = f"{API_BASE}pseudo-names/{pseudo_id}/deactivate/"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(API_URL, headers=headers) as response:
                try:
                    return await response.json()
                except aiohttp.ContentTypeError:
                    text = await response.text()
                    logging.error(f"[deactivate_pseudo_name] Non-JSON response: {text}")
                    return {"error": "Non-JSON response from backend", "details": text}
    except Exception as e:
        logging.exception("Error in deactivate_pseudo_name")
        return {"error": f"Request failed: {str(e)}"}

async def purchase_pseudo_name(user_id: int, pseudo_id: int) -> dict:
    print(f"purchase_pseudo_name: user_id={user_id}, pseudo_id={pseudo_id}")
    headers = {'Content-Type': 'application/json'}
    payload = {"user": user_id, "pseudo_name": pseudo_id}
    API_URL = API_BASE + 'user-pseudo-names/'
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(API_URL, json=payload, headers=headers) as response:
                try:
                    return await response.json()
                except aiohttp.ContentTypeError:
                    text = await response.text()
                    logging.error(f"[purchase_pseudo_name] Non-JSON response: {text}")
                    return {"error": "Non-JSON response from backend", "details": text}
    except Exception as e:
        logging.exception("Error in purchase_pseudo_name")
        return {"error": f"Request failed: {str(e)}"}
