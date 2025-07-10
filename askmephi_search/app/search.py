from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from app.loader import get_questions
import numpy as np

# Глобальные переменные для индекса
VECTORIZER = None
MATRIX = None
QUESTIONS_CACHE = []

THRESHOLD = 0.6  # Порог схожести


def build_index():
    global VECTORIZER, MATRIX, QUESTIONS_CACHE
    questions = get_questions()
    texts = [q['content'] for q in questions]
    if not texts:
        VECTORIZER, MATRIX, QUESTIONS_CACHE = None, None, []
        return
    VECTORIZER = TfidfVectorizer().fit(texts)
    MATRIX = VECTORIZER.transform(texts)
    QUESTIONS_CACHE = questions

def find_similar_question(user_question: str):
    if VECTORIZER is None or MATRIX is None or MATRIX.shape[0] == 0 or not QUESTIONS_CACHE:
        return None
    user_vec = VECTORIZER.transform([user_question])
    sims = cosine_similarity(user_vec, MATRIX)[0]
    best_idx = np.argmax(sims)
    if sims[best_idx] >= THRESHOLD:
        return QUESTIONS_CACHE[best_idx]
    return None 