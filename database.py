import sqlite3
from contextlib import contextmanager

DATABASE = 'group_manager.db'

@contextmanager
def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    with get_db() as conn:
        # First check if the column exists
        columns = [col[1] for col in conn.execute("PRAGMA table_info(groups)")]
        
        # Create tables with all columns (including anti_spam)
        conn.execute('''CREATE TABLE IF NOT EXISTS groups (
            chat_id INTEGER PRIMARY KEY,
            group_name TEXT,
            welcome_msg TEXT,
            goodbye_msg TEXT,
            delete_interval INTEGER,
            allowed_languages TEXT,
            warn_limit INTEGER DEFAULT 3,
            bio_protection BOOLEAN DEFAULT 1,
            anti_spam BOOLEAN DEFAULT 0
        )''')

        # Only add column if it doesn't exist
        if 'anti_spam' not in columns:
            try:
                conn.execute('ALTER TABLE groups ADD COLUMN anti_spam BOOLEAN DEFAULT 0')
            except sqlite3.OperationalError:
                pass  # Column already exists

        # Create other tables
        conn.execute('''CREATE TABLE IF NOT EXISTS banned_words (
            chat_id INTEGER,
            word TEXT,
            PRIMARY KEY (chat_id, word)
        )''')
        
        conn.execute('''CREATE TABLE IF NOT EXISTS warnings (
            chat_id INTEGER,
            user_id INTEGER,
            count INTEGER DEFAULT 0,
            PRIMARY KEY (chat_id, user_id)
        )''')
