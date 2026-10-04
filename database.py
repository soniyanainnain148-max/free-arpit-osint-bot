
import os
import sqlite3
from datetime import datetime, timezone

DB_PATH = os.getenv("DB_PATH", "arpit_bot.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            credits INTEGER DEFAULT 10,
            is_blocked INTEGER DEFAULT 0,
            joined_at TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS searches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            search_type TEXT,
            query TEXT,
            created_at TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            user_id INTEGER PRIMARY KEY
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS broadcasts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message TEXT,
            sent_count INTEGER DEFAULT 0,
            created_at TEXT
        )
    """)

    cursor.execute("""
        INSERT OR IGNORE INTO settings (key, value)
        VALUES ('maintenance_mode', '0')
    """)

    conn.commit()
    conn.close()


def register_user(user_id, username=None, first_name=None):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR IGNORE INTO users
        (user_id, username, first_name, credits, joined_at)
        VALUES (?, ?, ?, 10, ?)
    """, (
        user_id,
        username,
        first_name,
        datetime.now(timezone.utc).isoformat()
    ))

    cursor.execute("""
        UPDATE users
        SET username = ?, first_name = ?
        WHERE user_id = ?
    """, (username, first_name, user_id))

    conn.commit()
    conn.close()


def get_user(user_id):
    conn = get_db()
    user = conn.execute(
        "SELECT * FROM users WHERE user_id = ?",
        (user_id,)
    ).fetchone()
    conn.close()
    return user


def add_credits(user_id, amount):
    conn = get_db()
    conn.execute("""
        UPDATE users
        SET credits = credits + ?
        WHERE user_id = ?
    """, (amount, user_id))
    conn.commit()
    conn.close()


def deduct_credit(user_id):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE users
        SET credits = credits - 1
        WHERE user_id = ?
        AND credits > 0
        AND is_blocked = 0
    """, (user_id,))

    success = cursor.rowcount > 0

    conn.commit()
    conn.close()

    return success


def is_blocked(user_id):
    user = get_user(user_id)
    return bool(user["is_blocked"]) if user else False


def set_blocked(user_id, blocked=True):
    conn = get_db()
    conn.execute("""
        UPDATE users
        SET is_blocked = ?
        WHERE user_id = ?
    """, (int(blocked), user_id))
    conn.commit()
    conn.close()


def log_search(user_id, search_type, query):
    conn = get_db()
    conn.execute("""
        INSERT INTO searches
        (user_id, search_type, query, created_at)
        VALUES (?, ?, ?, ?)
    """, (
        user_id,
        search_type,
        query,
        datetime.now(timezone.utc).isoformat()
    ))
    conn.commit()
    conn.close()


def get_stats():
    conn = get_db()

    total_users = conn.execute(
        "SELECT COUNT(*) FROM users"
    ).fetchone()[0]

    blocked_users = conn.execute(
        "SELECT COUNT(*) FROM users WHERE is_blocked = 1"
    ).fetchone()[0]

    total_searches = conn.execute(
        "SELECT COUNT(*) FROM searches"
    ).fetchone()[0]

    total_credits = conn.execute(
        "SELECT COALESCE(SUM(credits), 0) FROM users"
    ).fetchone()[0]

    conn.close()

    return {
        "total_users": total_users,
        "blocked_users": blocked_users,
        "total_searches": total_searches,
        "total_credits": total_credits
    }


def get_all_users():
    conn = get_db()
    users = conn.execute(
        "SELECT * FROM users ORDER BY joined_at DESC"
    ).fetchall()
    conn.close()
    return users


def get_all_user_ids():
    conn = get_db()
    users = conn.execute(
        "SELECT user_id FROM users WHERE is_blocked = 0"
    ).fetchall()
    conn.close()
    return [user["user_id"] for user in users]


def get_recent_searches(limit=20):
    conn = get_db()
    searches = conn.execute("""
        SELECT * FROM searches
        ORDER BY id DESC
        LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return searches


def get_setting(key, default=None):
    conn = get_db()
    row = conn.execute(
        "SELECT value FROM settings WHERE key = ?",
        (key,)
    ).fetchone()
    conn.close()

    return row["value"] if row else default


def set_setting(key, value):
    conn = get_db()
    conn.execute("""
        INSERT INTO settings (key, value)
        VALUES (?, ?)
        ON CONFLICT(key)
        DO UPDATE SET value = excluded.value
    """, (key, str(value)))
    conn.commit()
    conn.close()


def add_admin(user_id):
    conn = get_db()
    conn.execute(
        "INSERT OR IGNORE INTO admins (user_id) VALUES (?)",
        (user_id,)
    )
    conn.commit()
    conn.close()


def is_admin(user_id):
    conn = get_db()
    result = conn.execute(
        "SELECT 1 FROM admins WHERE user_id = ?",
        (user_id,)
    ).fetchone()
    conn.close()
    return result is not None


def save_broadcast(message, sent_count):
    conn = get_db()
    conn.execute("""
        INSERT INTO broadcasts (message, sent_count, created_at)
        VALUES (?, ?, ?)
    """, (
        message,
        sent_count,
        datetime.now(timezone.utc).isoformat()
    ))
    conn.commit()
    conn.close()
