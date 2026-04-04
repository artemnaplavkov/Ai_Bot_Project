import sqlite3
import datetime

DB_NAME = "chatbot.db"

def init_db():
    """Создаёт таблицу logs, если её нет, и добавляет недостающие колонки intent и city."""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    # Создаём таблицу с базовыми полями
    cur.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            user_message TEXT NOT NULL,
            bot_response TEXT NOT NULL
        )
    """)
    # Проверяем наличие нужных колонок
    cur.execute("PRAGMA table_info(logs)")
    columns = [col[1] for col in cur.fetchall()]
    if 'intent' not in columns:
        cur.execute("ALTER TABLE logs ADD COLUMN intent TEXT")
    if 'city' not in columns:
        cur.execute("ALTER TABLE logs ADD COLUMN city TEXT")
    conn.commit()
    conn.close()

def save_log(user_message: str, bot_response: str, intent: str = None, city: str = None):
    """Сохраняет диалог в БД вместе с информацией об интенте и городе."""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute(
        "INSERT INTO logs (timestamp, user_message, bot_response, intent, city) VALUES (?, ?, ?, ?, ?)",
        (timestamp, user_message, bot_response, intent, city)
    )
    conn.commit()
    conn.close()