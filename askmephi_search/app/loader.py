import requests
from app.config import API_URL

# Глобальный кэш вопросов
QUESTIONS = []

def fetch_questions():
    """Загружает все опубликованные вопросы из API."""
    questions = []
    page = 1
    while True:
        url = f"{API_URL}&page={page}&page_size=1000"
        resp = requests.get(url)
        if resp.status_code != 200:
            break
        data = resp.json()
        results = data.get('results', [])
        if not results:
            break
        for post in results:
            if post.get('content') and post.get('channel_message_id'):
                questions.append({
                    'id': post['id'],
                    'content': post['content'],
                    'tg_id': post['channel_message_id'],
                })
        if not data.get('next'):
            break
        page += 1
    return questions

def update_questions():
    global QUESTIONS
    QUESTIONS = fetch_questions()

def get_questions():
    return QUESTIONS 