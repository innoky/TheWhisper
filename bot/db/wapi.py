import aiohttp
import logging
import asyncio
import json
from datetime import datetime

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
    

    API_URL = 'http://backend:8000/api/users/new/'

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(API_URL, json=payload, headers=headers) as response:
                return
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
    API_URL = 'http://backend:8000/api/post/get_last'  # URL вашего API

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(API_URL, headers=headers) as response:
                if response.status == 200:
                    return await response.json()  # Возвращаем JSON-ответ
                else:
                    return {
                        "error": f"API request failed with status {response.status}",
                        "details": await response.text()
                    }
    except Exception as e:
        logging.exception("Error in get_last_post")
        return {"error": f"Request failed: {str(e)}"}
    
async def try_create_post(author_id, content, post_time, telegram_id) -> dict:
    """
    Создает новый пост с указанным временем публикации.
    
    Args:
        post_time: datetime объект или строка в ISO формате.
    """
    headers = {'Content-Type': 'application/json'}
    
    # Преобразуем datetime в строку, если это необходимо
    if isinstance(post_time, datetime):
        post_time_str = post_time.isoformat()
    else:
        post_time_str = post_time  # Предполагаем, что это уже строка

    payload = {
        "author_id": author_id,
        "content": content,
        "posted_at": post_time_str,  # Используем строку вместо datetime
        "telegram_id": telegram_id,
        "is_posted": False,
        "is_rejected": False
    }
    
    API_URL = 'http://backend:8000/api/post/new/'

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(API_URL, json=payload, headers=headers) as response:
                return await response.json()  # Возвращаем ответ сервера
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
    API_URL = 'http://backend:8000/api/post/get_recent'  # URL вашего API

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(API_URL, headers=headers) as response:
                if response.status == 200:
                    return await response.json() 
                else:
                    return {
                        "error": f"API request failed with status {response.status}",
                        "details": await response.text()
                    }
    except Exception as e:
        logging.exception("Error in get_last_post")
        return {"error": f"Request failed: {str(e)}"}

async def mark_post_as_posted(post_id):
     
    headers = {'Content-Type': 'application/json'}
    
    # Преобразуем datetime в строку, если это необходимо
    
    payload = {
        "post_id": post_id
    }
    
    API_URL = 'http://backend:8000/api/post/mark_as_posted/'

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(API_URL, json=payload, headers=headers) as response:
                return await response.json() 
               
    except Exception as e:
        logging.exception("Error in try_create_post")
        return {"error": f"Request failed: {str(e)}"}

async def mark_post_as_rejected(post_id):
    headers = {'Content-Type': 'application/json'}
    
    # Преобразуем datetime в строку, если это необходимо
    
    payload = {
        "post_id": post_id
    }
    
    API_URL = 'http://backend:8000/api/post/mark_as_rejected/'

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(API_URL, json=payload, headers=headers) as response:
                return await response.json() 
    except Exception as e:
        logging.exception("Error in try_create_post")
        return {"error": f"Request failed: {str(e)}"}
    
async def leave_anon_comment(telegram_id, post_id, user_id, content):
    """
    Создает новый анонимный комментарий.
    """
    headers = {'Content-Type': 'application/json'}
    
    # Преобразуем datetime в строку, если это необходимо
   
    payload = {
        "post": post_id,
        "author_id": user_id,
        "content": content,
        "telegram_id": telegram_id
    }
    
    API_URL = 'http://backend:8000/api/comment/new/'
    print("HEREEE")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(API_URL, json=payload, headers=headers) as response:
                result = await response.json()  # Возвращаем ответ сервера
                print(result)
                return result
    except Exception as e:
        logging.exception("Error in try_create_post")
        return {"error": f"Request failed: {str(e)}"}

async def get_user_pseudo_names(user_id):
    headers = {'Accept': 'application/json'}
    API_URL = f'http://backend:8000/api/users/{user_id}/pseudo-names/'  # URL вашего API

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(API_URL, headers=headers) as response:
                if response.status == 200:
                    result = await response.json() 
                    results = result.get("results", [])
                    pseudo_names = []
                    for item in results:
                      if isinstance(item, dict) and "pseudo_name" in item:
                        pseudo_data = item["pseudo_name"]
                        if isinstance(pseudo_data, dict) and "name" in pseudo_data:
                            pseudo_names.append((pseudo_data['id'],pseudo_data["name"]))
    
                    return pseudo_names

                else:
                    return {
                        "error": f"API request failed with status {response.status}",
                        "details": await response.text()
                    }
    except Exception as e:
        logging.exception("Error in get_last_post")
        return {"error": f"Request failed: {str(e)}"}

async def is_user_banned(user_id):
    headers = {'Accept': 'application/json'}
    API_URL = 'http://backend:8000/api/users/exists/'  # URL вашего API


    payload = {
        "user_id":user_id
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(API_URL, json=payload,headers=headers) as response:
                if response.status == 200:
                    result = await response.json() 
                    if result['is_banned']:
                        return True
                    return False
                   
                else:
                    return {
                        "error": f"API request failed with status {response.status}",
                        "details": await response.text()
                    }
    except Exception as e:
        logging.exception("Error in get_last_post")
        return {"error": f"Request failed: {str(e)}"}
    
async def ban_user(user_id):
    headers = {'Accept': 'application/json'}
    API_URL = f'http://backend:8000/api/users/{user_id}/ban/'  # URL вашего API

    if (await is_user_banned(user_id)):
        return "User already banned"
    else:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(API_URL,headers=headers) as response:
                    if response.status == 200:
                        print (await response.json() )
                        return
                    else:
                        return {
                            "error": f"API request failed with status {response.status}",
                            "details": await response.text()
                        }
        except Exception as e:
            logging.exception("Error in get_last_post")
            return {"error": f"Request failed: {str(e)}"}
 
async def unban_user(user_id):
    headers = {'Accept': 'application/json'}
    API_URL = f'http://backend:8000/api/users/{user_id}/ban/'  # URL вашего API

    if not(await is_user_banned(user_id)):
        return "User already гтbanned"
    else:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(API_URL,headers=headers) as response:
                    if response.status == 200:
                        print (await response.json() )
                        return
                    else:
                        return {
                            "error": f"API request failed with status {response.status}",
                            "details": await response.text()
                        }
        except Exception as e:
            logging.exception("Error in get_last_post")
            return {"error": f"Request failed: {str(e)}"}
