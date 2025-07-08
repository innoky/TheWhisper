from fastapi import FastAPI, Query
from app.search import find_similar_question, build_index
from app.loader import update_questions, get_questions
from app.config import CHANNEL_ID, UPDATE_INTERVAL_MINUTES
import threading
import time

app = FastAPI()

@app.on_event("startup")
def startup_event():
    def periodic_update():
        while True:
            update_questions()
            build_index()
            time.sleep(UPDATE_INTERVAL_MINUTES * 60)
    # Первая загрузка
    update_questions()
    build_index()
    # Запуск фонового потока
    thread = threading.Thread(target=periodic_update, daemon=True)
    thread.start()

@app.get("/search/")
def search(question: str = Query(..., description="Вопрос пользователя")):
    result = find_similar_question(question)
    if result:
        link = f"https://t.me/c/{CHANNEL_ID}/{result['tg_id']}"
        return {"found": True, "link": link, "id": result["id"]}
    return {"found": False}

@app.get("/all_posts/")
def all_posts():
    """Возвращает все посты, которые видит микросервис (для теста)."""
    return get_questions() 