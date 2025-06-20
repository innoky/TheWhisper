import os
from dotenv import load_dotenv
from urllib.parse import quote_plus

load_dotenv('.env')

BOT_TOKEN = os.getenv("BOT_TOKEN")
TARGET_CHAT_ID = int(os.getenv("TARGET_CHAT_ID"))
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID"))
BOT_NAME = os.getenv("BOT_NAME")
CHAT_ID = int(os.getenv("CHAT_ID"))
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")

if not all([BOT_TOKEN, TARGET_CHAT_ID, ADMIN_CHAT_ID, BOT_NAME, CHAT_ID, DB_USER, DB_PASSWORD, DB_HOST, DB_NAME]):
    raise RuntimeError("One or more required environment variables are missing!")

DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{quote_plus(DB_PASSWORD)}@{DB_HOST}:5432/{DB_NAME}" 