import aiohttp
import logging
import asyncio

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
        "firstname": firstname,
        "lastname": lastname,
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

async def main():
    result = await try_create_user(124, "testuser", "John", "Doe")

asyncio.run(main())