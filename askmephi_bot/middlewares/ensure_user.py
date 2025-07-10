import logging
from db.wapi import try_create_user

class EnsureUserMiddleware:
    async def __call__(self, handler, event, data):
        user = getattr(event, "from_user", None)
        if user and not getattr(user, "is_bot", False):
            print(f"!!! [EnsureUserMiddleware] try_create_user for {user.id} ({user.username})")
            logging.info(f"[EnsureUserMiddleware] try_create_user for {user.id} ({user.username})")
            result = await try_create_user(
                user.id,
                user.username,
                user.first_name,
                user.last_name
            )
            print(f"!!! [EnsureUserMiddleware] try_create_user result: {result}")
            logging.info(f"[EnsureUserMiddleware] try_create_user result: {result}")
        return await handler(event, data) 