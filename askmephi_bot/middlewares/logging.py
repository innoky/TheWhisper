import logging
 
class LoggingMiddleware:
    async def __call__(self, handler, event, data):
        logging.info(f"Update: {event}")
        return await handler(event, data)