import os

BLACKLIST_FILE = "blacklist.txt"

def load_blacklist():
    if not os.path.exists(BLACKLIST_FILE):
        return set()
    with open(BLACKLIST_FILE, "r") as f:
        return set(line.strip() for line in f if line.strip().isdigit())

def add_to_blacklist(user_id: int):
    with open(BLACKLIST_FILE, "a") as f:
        f.write(f"{user_id}\n") 