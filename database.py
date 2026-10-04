
import os
import psycopg
from psycopg.rows import dict_row

DATABASE_URL = os.getenv("DATABASE_URL")


def get_connection():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL environment variable is missing")

    return psycopg.connect(
        DATABASE_URL,
        row_factory=dict_row,
        connect_timeout=10
    )


def init_db():
    with get_connection() as conn:
        with conn.cursor() as cur:

            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    credits INTEGER DEFAULT 0,
                    is_blocked BOOLEAN DEFAULT FALSE,
                    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS searches (
                    id BIGSERIAL PRIMARY KEY,
                    user_id BIGINT,
                    search_type TEXT,
                    query TEXT,
                    result TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS admins (
                    user_id BIGINT PRIMARY KEY,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS broadcasts (
                    id BIGSERIAL PRIMARY KEY,
                    message TEXT,
                    sent_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)


def register_user(user_id, username=None, first_name=None):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO users (user_id, username, first_name)
                VALUES (%s, %s, %s)
                ON CONFLICT (user_id) DO UPDATE SET
                    username = EXCLUDED.username,
                    first_name = EXCLUDED.first_name
            """, (user_id, username, first_name))


def get_user(user_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM users WHERE user_id = %s",
                (user_id,)
            )
            return cur.fetchone()


def add_credits(user_id, amount):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE users
                SET credits = credits + %s
                WHERE user_id = %s
            """, (amount, user_id))
            return cur.rowcount > 0


def deduct_credit(user_id, amount=1):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE users
                SET credits = credits - %s
                WHERE user_id = %s AND credits >= %s
                RETURNING credits
            """, (amount, user_id, amount))
            return cur.fetchone() is not None


def is_blocked(user_id):
    user = get_user(user_id)
    return bool(user and user["is_blocked"])


def set_blocked(user_id, blocked=True):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE users
                SET is_blocked = %s
                WHERE user_id = %s
            """, (blocked, user_id))
            return cur.rowcount > 0


def log_search(user_id, search_type, query, result=""):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO searches
                (user_id, search_type, query, result)
                VALUES (%s, %s, %s, %s)
            """, (user_id, search_type, query, str(result)))


def get_stats():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS total_users FROM users")
            total_users = cur.fetchone()["total_users"]

            cur.execute("SELECT COUNT(*) AS total_searches FROM searches")
            total_searches = cur.fetchone()["total_searches"]

            cur.execute("""
                SELECT COALESCE(SUM(credits), 0) AS total_credits
                FROM users
            """)
            total_credits = cur.fetchone()["total_credits"]

            cur.execute("""
                SELECT COUNT(*) AS blocked_users
                FROM users WHERE is_blocked = TRUE
            """)
            blocked_users = cur.fetchone()["blocked_users"]

            return {
                "total_users": total_users,
                "total_searches": total_searches,
                "total_credits": total_credits,
                "blocked_users": blocked_users
            }


def get_all_users():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM users
                ORDER BY joined_at DESC
            """)
            return cur.fetchall()


def get_all_user_ids():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT user_id FROM users")
            return [row["user_id"] for row in cur.fetchall()]


def get_recent_searches(limit=50):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM searches
                ORDER BY created_at DESC
                LIMIT %s
            """, (limit,))
            return cur.fetchall()


def get_setting(key, default=None):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT value FROM settings WHERE key = %s",
                (key,)
            )
            row = cur.fetchone()
            return row["value"] if row else default


def set_setting(key, value):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO settings (key, value)
                VALUES (%s, %s)
                ON CONFLICT (key) DO UPDATE
                SET value = EXCLUDED.value
            """, (key, str(value)))


def add_admin(user_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO admins (user_id)
                VALUES (%s)
                ON CONFLICT (user_id) DO NOTHING
            """, (user_id,))


def is_admin(user_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM admins WHERE user_id = %s",
                (user_id,)
            )
            return cur.fetchone() is not None


def save_broadcast(message, sent_count=0):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO broadcasts (message, sent_count)
                VALUES (%s, %s)
            """, (message, sent_count))
