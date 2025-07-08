import os
API_URL = "http://backend:8000/api/ask-posts/?is_posted=true&ordering=-channel_posted_at"
CHANNEL_ID = os.getenv("ORACLE_CHANNEL_ID").replace('-100','')  
UPDATE_INTERVAL_MINUTES = 60  # Период обновления индекса (в минутах) 