import sqlite3
import random
import string
import json
from typing import Optional, Dict, Any

class Database:
    def __init__(self, db_path: str = "giftguard.db"):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._init_db()

    def _init_db(self):
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS deals (
                deal_id TEXT PRIMARY KEY,
                seller_id INTEGER,
                buyer_id INTEGER,
                deal_type TEXT,
                description TEXT,
                amount REAL,
                currency TEXT DEFAULT 'RUB',
                status TEXT DEFAULT 'waiting',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                paid_at TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                balance REAL DEFAULT 0,
                frozen_balance REAL DEFAULT 0,
                seller_deals INTEGER DEFAULT 0,
                buyer_deals INTEGER DEFAULT 0,
                rating REAL DEFAULT 5.0,
                requisites TEXT DEFAULT '{}',
                language TEXT DEFAULT 'ru'
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stats (
                id INTEGER PRIMARY KEY,
                total_paid REAL DEFAULT 0,
                total_deals INTEGER DEFAULT 0
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                user_id INTEGER PRIMARY KEY
            )
        """)
        cursor.execute(
            "INSERT OR IGNORE INTO stats (id, total_paid, total_deals) VALUES (1, 0, 0)"
        )
        self.conn.commit()

    def add_admin(self, user_id: int):
        cursor = self.conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (user_id,))
        self.conn.commit()

    def remove_admin(self, user_id: int):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM admins WHERE user_id = ?", (user_id,))
        self.conn.commit()

    def get_admins(self) -> list:
        cursor = self.conn.cursor()
        cursor.execute("SELECT user_id FROM admins")
        return [row[0] for row in cursor.fetchall()]

    def update_language(self, user_id: int, lang: str):
        cursor = self.conn.cursor()
        cursor.execute("UPDATE users SET language = ? WHERE user_id = ?", (lang, user_id))
        self.conn.commit()

    def get_user_lang(self, user_id: int) -> str:
        user = self.get_user(user_id)
        return user[9] if user and len(user) > 9 else 'ru'

    def get_all_users(self) -> list:
        cursor = self.conn.cursor()
        cursor.execute("SELECT user_id FROM users")
        return [row[0] for row in cursor.fetchall()]

    def get_user(self, user_id: int) -> Optional[tuple]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        return cursor.fetchone()

    def save_user(self, user_id: int, username: str, first_name: str):
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT OR IGNORE INTO users (user_id, username, first_name) VALUES (?, ?, ?)",
            (user_id, username, first_name),
        )
        self.conn.commit()

    def update_requisites(self, user_id: int, req_type: str, value: str):
        cursor = self.conn.cursor()
        user = self.get_user(user_id)
        requisites = {}
        if user and user[8]:
            try:
                requisites = json.loads(user[8])
            except:
                pass
        requisites[req_type] = value
        cursor.execute(
            "UPDATE users SET requisites = ? WHERE user_id = ?",
            (json.dumps(requisites), user_id),
        )
        self.conn.commit()

    def create_deal(
        self,
        seller_id: int,
        deal_type: str,
        description: str,
        amount: float,
        currency: str,
    ) -> str:
        deal_id = "".join(random.choices(string.digits, k=6))
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO deals (deal_id, seller_id, deal_type, description, amount, currency) VALUES (?, ?, ?, ?, ?, ?)",
            (deal_id, seller_id, deal_type, description, amount, currency),
        )
        cursor.execute("UPDATE stats SET total_deals = total_deals + 1 WHERE id = 1")
        self.conn.commit()
        return deal_id

    def get_deal(self, deal_id: str) -> Optional[Dict[str, Any]]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM deals WHERE deal_id = ?", (deal_id,))
        row = cursor.fetchone()
        if row:
            return {
                "deal_id": row[0],
                "seller_id": row[1],
                "buyer_id": row[2],
                "deal_type": row[3],
                "description": row[4],
                "amount": row[5],
                "currency": row[6],
                "status": row[7],
                "created_at": row[8],
                "paid_at": row[9],
            }
        return None

    def set_buyer(self, deal_id: str, buyer_id: int):
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE deals SET buyer_id = ? WHERE deal_id = ?", (buyer_id, deal_id)
        )
        self.conn.commit()

    def mark_paid(self, deal_id: str):
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE deals SET status = 'paid', paid_at = CURRENT_TIMESTAMP WHERE deal_id = ?",
            (deal_id,),
        )
        cursor.execute(
            "UPDATE stats SET total_paid = total_paid + (SELECT amount FROM deals WHERE deal_id = ?) WHERE id = 1",
            (deal_id,),
        )
        self.conn.commit()

    def get_user_deals(self, user_id: int) -> list:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM deals WHERE seller_id = ? ORDER BY created_at DESC",
            (user_id,),
        )
        return cursor.fetchall()

    def get_stats(self) -> Optional[tuple]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM stats WHERE id = 1")
        return cursor.fetchone()

db = Database()
