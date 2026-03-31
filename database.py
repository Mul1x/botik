import sqlite3
from contextlib import contextmanager
from typing import Optional, List, Dict, Any

DATABASE_PATH = "gifts_ok.db"


@contextmanager
def get_db():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Таблица пользователей
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Таблица реквизитов пользователя
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_wallets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                wallet_type TEXT,
                wallet_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        # Таблица сделок
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS deals (
                deal_id TEXT PRIMARY KEY,
                seller_id INTEGER,
                buyer_id INTEGER,
                amount_rub INTEGER,
                description TEXT,
                status TEXT DEFAULT 'waiting_buyer',
                payment_address TEXT,
                payment_memo TEXT,
                amount_usdt REAL,
                amount_ton REAL,
                amount_px REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Таблица админов
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                added_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Добавляем главного админа если его нет
        from config import MAIN_ADMIN_ID
        cursor.execute(
            "INSERT OR IGNORE INTO admins (user_id, username) VALUES (?, ?)",
            (MAIN_ADMIN_ID, "main_admin")
        )


def add_user(user_id: int, username: str = None, full_name: str = None):
    with get_db() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO users (user_id, username, full_name) VALUES (?, ?, ?)",
            (user_id, username, full_name)
        )


def get_user_wallets(user_id: int) -> List[Dict[str, Any]]:
    with get_db() as conn:
        cursor = conn.execute(
            "SELECT id, wallet_type, wallet_data FROM user_wallets WHERE user_id = ?",
            (user_id,)
        )
        return [dict(row) for row in cursor.fetchall()]


def add_wallet(user_id: int, wallet_type: str, wallet_data: str):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO user_wallets (user_id, wallet_type, wallet_data) VALUES (?, ?, ?)",
            (user_id, wallet_type, wallet_data)
        )


def update_wallet(wallet_id: int, wallet_data: str):
    with get_db() as conn:
        conn.execute(
            "UPDATE user_wallets SET wallet_data = ? WHERE id = ?",
            (wallet_data, wallet_id)
        )


def delete_wallet(wallet_id: int):
    with get_db() as conn:
        conn.execute("DELETE FROM user_wallets WHERE id = ?", (wallet_id,))


def create_deal(deal_id: str, seller_id: int, amount_rub: int, description: str) -> bool:
    """Создание сделки, генерация адреса для оплаты"""
    import random
    import string
    
    # Генерация адреса и мемо (для демо используем статичные данные)
    payment_address = "UQB7hOU1thMw-QOE31X2ZZ0sYS16NfZtQsAckCEpy5831Ra-"
    payment_memo = deal_id
    
    # Расчет сумм в криптовалюте (условные курсы)
    amount_usdt = round(amount_rub / 90, 2)  # 1 USDT ~ 90 RUB
    amount_ton = round(amount_usdt / 6.5, 2)  # 1 TON ~ 6.5 USDT
    amount_px = round(amount_usdt * 42, 2)  # для демо
    
    with get_db() as conn:
        conn.execute("""
            INSERT INTO deals 
            (deal_id, seller_id, amount_rub, description, payment_address, payment_memo, 
             amount_usdt, amount_ton, amount_px)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (deal_id, seller_id, amount_rub, description, payment_address, payment_memo,
              amount_usdt, amount_ton, amount_px))
    return True


def get_deal(deal_id: str) -> Optional[Dict[str, Any]]:
    with get_db() as conn:
        cursor = conn.execute("SELECT * FROM deals WHERE deal_id = ?", (deal_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def update_deal_buyer(deal_id: str, buyer_id: int):
    with get_db() as conn:
        conn.execute(
            "UPDATE deals SET buyer_id = ?, status = 'waiting_payment' WHERE deal_id = ?",
            (buyer_id, deal_id)
        )


def update_deal_status(deal_id: str, status: str):
    with get_db() as conn:
        conn.execute(
            "UPDATE deals SET status = ? WHERE deal_id = ?",
            (status, deal_id)
        )


def is_admin(user_id: int) -> bool:
    with get_db() as conn:
        cursor = conn.execute(
            "SELECT 1 FROM admins WHERE user_id = ?",
            (user_id,)
        )
        return cursor.fetchone() is not None


def get_admins() -> List[Dict[str, Any]]:
    with get_db() as conn:
        cursor = conn.execute("SELECT user_id, username FROM admins")
        return [dict(row) for row in cursor.fetchall()]


def add_admin(user_id: int, username: str, added_by: int):
    with get_db() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO admins (user_id, username, added_by) VALUES (?, ?, ?)",
            (user_id, username, added_by)
        )


def remove_admin(user_id: int):
    from config import MAIN_ADMIN_ID
    if user_id == MAIN_ADMIN_ID:
        return False
    with get_db() as conn:
        conn.execute("DELETE FROM admins WHERE user_id = ?", (user_id,))
    return True


def user_has_wallets(user_id: int) -> bool:
    with get_db() as conn:
        cursor = conn.execute(
            "SELECT 1 FROM user_wallets WHERE user_id = ?",
            (user_id,)
        )
        return cursor.fetchone() is not None
