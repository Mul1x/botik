import asyncio
import logging
import sqlite3
import random
import string
import json
import os
from datetime import datetime
from typing import Optional, Dict, Any

from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
    Message,
    FSInputFile,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

load_dotenv()

# Конфигурация
BOT_TOKEN = os.getenv("BOT_TOKEN", "8674178298:AAFuv0b3fTCANT-ADw3INJtxRKN-WCCLryA")
BOT_USERNAME = os.getenv("BOT_USERNAME", "garantmoskowbot")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "7687750743,8072028362").split(",")]

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== БД ====================


class Database:
    def __init__(self):
        self.conn = sqlite3.connect("giftguard.db", check_same_thread=False)
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
                requisites TEXT DEFAULT '{}'
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stats (
                id INTEGER PRIMARY KEY,
                total_paid REAL DEFAULT 0,
                total_deals INTEGER DEFAULT 0
            )
        """)
        cursor.execute(
            "INSERT OR IGNORE INTO stats (id, total_paid, total_deals) VALUES (1, 0, 0)"
        )
        self.conn.commit()

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

# ==================== FSM СОСТОЯНИЯ ====================


class DealStates(StatesGroup):
    waiting_deal_type = State()
    waiting_description = State()
    waiting_amount = State()
    waiting_currency = State()


class RequisitesStates(StatesGroup):
    waiting_value = State()


class ScamStates(StatesGroup):
    waiting_username = State()


class WithdrawStates(StatesGroup):
    waiting_amount = State()


# ==================== КЛАВИАТУРЫ ====================


def main_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🟢 Новая сделка", callback_data="new_deal"),
        InlineKeyboardButton(text="📋 Мои сделки", callback_data="my_deals")
    )
    builder.row(
        InlineKeyboardButton(text="👤 Профиль", callback_data="profile"),
        InlineKeyboardButton(text="💳 Реквизиты", callback_data="requisites")
    )
    builder.row(
        InlineKeyboardButton(text="💰 Вывод", callback_data="withdraw"),
        InlineKeyboardButton(text="⚠️ Скам база", callback_data="scam_base")
    )
    builder.row(
        InlineKeyboardButton(text="📢 Канал", url="https://t.me/GiftGuard_channel", style="primary"),
        InlineKeyboardButton(text="🆘 Поддержка", url="https://t.me/GiftGuard_support", style="primary")
    )
    return builder.as_markup()

def deal_type_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🎁 Подарок", callback_data="type_gift"),
        InlineKeyboardButton(text="👤 Аккаунт", callback_data="type_account")
    )
    builder.row(
        InlineKeyboardButton(text="📦 Другое", callback_data="type_other")
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Назад в меню", callback_data="menu")
    )
    return builder.as_markup()

def currency_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="RUB", callback_data="cur_RUB"),
        InlineKeyboardButton(text="KZT", callback_data="cur_KZT"),
        InlineKeyboardButton(text="UAH", callback_data="cur_UAH")
    )
    builder.row(
        InlineKeyboardButton(text="BYN", callback_data="cur_BYN"),
        InlineKeyboardButton(text="EUR", callback_data="cur_EUR"),
        InlineKeyboardButton(text="USD", callback_data="cur_USD")
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Назад к типу", callback_data="back_to_deal_type")
    )
    return builder.as_markup()
def currency_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="RUB", callback_data="cur_RUB"),
        InlineKeyboardButton(text="KZT", callback_data="cur_KZT"),
        InlineKeyboardButton(text="UAH", callback_data="cur_UAH")
    )
    builder.row(
        InlineKeyboardButton(text="BYN", callback_data="cur_BYN"),
        InlineKeyboardButton(text="EUR", callback_data="cur_EUR"),
        InlineKeyboardButton(text="USD", callback_data="cur_USD")
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Назад к типу", callback_data="back_to_deal_type")
    )
    return builder.as_markup()

def requisites_edit_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="💳 Карта", callback_data="req_card"),
        InlineKeyboardButton(text="🇰🇿 Kaspi", callback_data="req_kaspi")
    )
    builder.row(
        InlineKeyboardButton(text="💸 QIWI", callback_data="req_qiwi"),
        InlineKeyboardButton(text="💰 ЮMoney", callback_data="req_yoomoney")
    )
    builder.row(
        InlineKeyboardButton(text="🌐 WebMoney", callback_data="req_webmoney")
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Назад в меню", callback_data="menu")
    )
    return builder.as_markup()

def deal_type_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🎁 Подарок", callback_data="type_gift"),
        InlineKeyboardButton(text="👤 Аккаунт", callback_data="type_account")
    )
    builder.row(
        InlineKeyboardButton(text="📦 Другое", callback_data="type_other")
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Назад в меню", callback_data="menu")
    )
    return builder.as_markup()

def scam_base_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔍 Проверить пользователя", callback_data="check_user")
    )
    builder.row(
        InlineKeyboardButton(text="🚨 Сообщить о скамере", callback_data="report_scam", style="danger")
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Назад в меню", callback_data="menu")
    )
    return builder.as_markup()

def back_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="◀️ Назад в меню", callback_data="menu"))
    return builder.as_markup()

def deal_confirm_menu(deal_id: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Оплатить", callback_data=f"pay_{deal_id}", style="success"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="menu", style="danger")
    )

def requisites_edit_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="💳 Карта", callback_data="req_card"),
        InlineKeyboardButton(text="🇰🇿 Kaspi", callback_data="req_kaspi")
    )
    builder.row(
        InlineKeyboardButton(text="💸 QIWI", callback_data="req_qiwi"),
        InlineKeyboardButton(text="💰 ЮMoney", callback_data="req_yoomoney")
    )
    builder.row(
        InlineKeyboardButton(text="🌐 WebMoney", callback_data="req_webmoney")
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Назад в меню", callback_data="menu")
    )
    return builder.as_markup()

def deal_type_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🎁 Подарок", callback_data="type_gift", style="primary"),
        InlineKeyboardButton(text="👤 Аккаунт", callback_data="type_account", style="primary")
    )
    builder.row(
        InlineKeyboardButton(text="📦 Другое", callback_data="type_other", style="primary")
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Назад в меню", callback_data="menu")
    )
    return builder.as_markup()


def deal_type_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🎁 Подарок", callback_data="type_gift"),
        InlineKeyboardButton(text="👤 Аккаунт", callback_data="type_account"),
    )
    builder.row(InlineKeyboardButton(text="📦 Другое", callback_data="type_other"))
    builder.row(
        InlineKeyboardButton(text="◀️ Назад в меню", callback_data="back_to_menu")
    )
    return builder.as_markup()


def currency_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="RUB", callback_data="cur_RUB", style="primary"),
        InlineKeyboardButton(text="KZT", callback_data="cur_KZT", style="primary"),
        InlineKeyboardButton(text="UAH", callback_data="cur_UAH", style="primary")
    )
    builder.row(
        InlineKeyboardButton(text="BYN", callback_data="cur_BYN", style="primary"),
        InlineKeyboardButton(text="EUR", callback_data="cur_EUR", style="primary"),
        InlineKeyboardButton(text="USD", callback_data="cur_USD", style="primary")
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Назад к типу", callback_data="back_to_deal_type")
    )
    return builder.as_markup()

def requisites_edit_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="💳 Карта", callback_data="req_card", style="primary"),
        InlineKeyboardButton(text="🇰🇿 Kaspi", callback_data="req_kaspi", style="primary")
    )
    builder.row(
        InlineKeyboardButton(text="💸 QIWI", callback_data="req_qiwi", style="primary"),
        InlineKeyboardButton(text="💰 ЮMoney", callback_data="req_yoomoney", style="primary")
    )
    builder.row(
        InlineKeyboardButton(text="🌐 WebMoney", callback_data="req_webmoney", style="primary")
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Назад в меню", callback_data="menu")
    )
    return builder.as_markup()

def scam_base_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔍 Проверить пользователя", callback_data="check_user", style="primary")
    )
    builder.row(
        InlineKeyboardButton(text="🚨 Сообщить о скамере", callback_data="report_scam", style="danger")
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Назад в меню", callback_data="menu")
    )
    return builder.as_markup()

def back_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="◀️ Назад в меню", callback_data="menu"))
    return builder.as_markup()

def deal_confirm_menu(deal_id: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Оплатить", callback_data=f"pay_{deal_id}", style="success"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="menu", style="danger")
    )
    return builder.as_markup()


def requisites_edit_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="💳 Карта", callback_data="req_card"),
        InlineKeyboardButton(text="🇰🇿 Kaspi", callback_data="req_kaspi"),
    )
    builder.row(
        InlineKeyboardButton(text="💸 QIWI", callback_data="req_qiwi"),
        InlineKeyboardButton(text="💰 ЮMoney", callback_data="req_yoomoney"),
    )
    builder.row(InlineKeyboardButton(text="🌐 WebMoney", callback_data="req_webmoney"))
    builder.row(InlineKeyboardButton(text="◀️ Назад в меню", callback_data="menu"))
    return builder.as_markup()


def scam_base_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="🔍 Проверить пользователя", callback_data="check_user"
        )
    )
    builder.row(
        InlineKeyboardButton(text="🚨 Сообщить о скамере", callback_data="report_scam")
    )
    builder.row(InlineKeyboardButton(text="◀️ Назад в меню", callback_data="menu"))
    return builder.as_markup()


def back_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🏠 Назад в меню", callback_data="menu"))
    return builder.as_markup()


def back_to_requisites() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="◀️ Назад к реквизитам", callback_data="requisites")
    )
    return builder.as_markup()


def format_amount(amount: float) -> str:
    return f"{amount:,.2f}".replace(",", " ")


def get_rating_stars(rating: float) -> str:
    return "★" * int(rating) + "☆" * (5 - int(rating))


# ==================== ОСНОВНЫЕ ОБРАБОТЧИКИ ====================


async def send_main_menu(target, user_id: int, username: str, first_name: str):
    user_data = db.get_user(user_id)
    rating = user_data[7] if user_data else 5.0
    deals_count = user_data[5] if user_data else 0
    stats = db.get_stats()
    total_paid = stats[1] if stats else 0

    text = f"""
<b>🛡️ GIFT GUARD</b>

Привет, {first_name}!
<b>Рейтинг:</b> {get_rating_stars(rating)} ({rating:.1f}/5) | <b>Сделок:</b> {deals_count}

Добро пожаловать в гарант-сервис для безопасных сделок!
GIFT GUARD — сервис, который предоставляет возможность <b>безопасно</b> продавать и покупать любые товары. Мы обеспечиваем <b>защиту обеих сторон</b>, прозрачные условия и <b>быстрые выплаты</b>.

---

<b>Статистика:</b>
- Выплачено: {format_amount(total_paid)} RUB
- Комиссия сервиса: 1.5%

Нажмите кнопки ниже, чтобы начать!
"""

    try:
        photo = FSInputFile("main.png")
        if isinstance(target, Message):
            await target.answer_photo(
                photo=photo,
                caption=text,
                parse_mode="HTML",
                reply_markup=main_menu(),
                show_caption_above_media=True # Новая фишка API, может помочь с версткой
            )
        elif isinstance(target, CallbackQuery):
            await target.message.answer_photo(
                photo=photo,
                caption=text,
                parse_mode="HTML",
                reply_markup=main_menu(),
                show_caption_above_media=True
            )
            try:
                await target.message.delete()            except:
                pass
    except Exception as e:
        logger.error(f"Error sending main menu: {e}")
        if isinstance(target, Message):
            await target.answer(
                text=text, parse_mode="HTML", reply_markup=main_menu()
            )
        elif isinstance(target, CallbackQuery):
            await target.message.answer(
                text=text, parse_mode="HTML", reply_markup=main_menu()
            )
            try:
                await target.message.delete()
            except:
                pass


# ==================== РЕГИСТРАЦИЯ ОБРАБОТЧИКОВ ====================


def register_handlers(dp: Dispatcher):
    @dp.message(Command("start"))
    async def cmd_start(message: Message, command: CommandObject):
        user = message.from_user
        db.save_user(user.id, user.username, user.first_name)

        # Проверка параметра сделки
        if command.args:
            deal_id = command.args.replace("deal_", "")
            deal = db.get_deal(deal_id)

            if deal and deal["status"] == "waiting":
                db.set_buyer(deal_id, user.id)
                deal = db.get_deal(deal_id)
                amount_str = format_amount(deal["amount"])
                seller = db.get_user(deal["seller_id"])

                text = f"""
📋 <b>СДЕЛКА #{deal["deal_id"]}</b>

👤 <b>Продавец:</b> {seller[2] if seller else "Пользователь"} @{seller[1] if seller else "no_username"}
📦 <b>Тип:</b> {deal["deal_type"]}
💰 <b>Сумма:</b> {amount_str} {deal["currency"]}

<b>Статус:</b> {"🟡 Ожидает оплаты" if deal["status"] == "waiting" else "🔵 Оплачено"}
"""
                builder = InlineKeyboardBuilder()
                if user.id in ADMIN_IDS:
                    builder.row(
                        InlineKeyboardButton(
                            text="✅ Я оплатил", callback_data=f"pay_{deal_id}"
                        )
                    )
                builder.row(
                    InlineKeyboardButton(text="◀️ Назад в меню", callback_data="menu")
                )

                await message.answer(
                    text, parse_mode="HTML", reply_markup=builder.as_markup()
                )
                return

        await send_main_menu(message, user.id, user.username, user.first_name)

    # ==================== НОВАЯ СДЕЛКА ====================

    @dp.callback_query(F.data == "new_deal")
    async def new_deal_handler(callback: CallbackQuery, state: FSMContext):
        await callback.answer()
        await callback.message.answer(
            "Выберите тип сделки:", reply_markup=deal_type_menu()
        )
        try:
            await callback.message.delete()
        except:
            pass
        await state.set_state(DealStates.waiting_deal_type)

    @dp.callback_query(F.data == "profile")
    async def profile_handler(callback: CallbackQuery):
        user_data = db.get_user(callback.from_user.id)
        if not user_data:
            db.save_user(
                callback.from_user.id,
                callback.from_user.username,
                callback.from_user.first_name,
            )
            user_data = db.get_user(callback.from_user.id)

        rating = user_data[7]
        deals_count = user_data[5] + user_data[6]
        balance = user_data[3]
        frozen = user_data[4]

        text = f"""
👤 <b>Профиль пользователя</b>

<b>ID:</b> <code>{callback.from_user.id}</code>
<b>Имя:</b> {callback.from_user.first_name}
<b>Username:</b> @{callback.from_user.username}

<b>Рейтинг:</b> {get_rating_stars(rating)} ({rating:.1f}/5)
<b>Всего сделок:</b> {deals_count}

💰 <b>Баланс:</b> {format_amount(balance)} RUB
❄️ <b>Заморожено:</b> {format_amount(frozen)} RUB
"""
        await callback.answer()
        await callback.message.answer(
            text, parse_mode="HTML", reply_markup=back_menu()
        )
        try:
            await callback.message.delete()
        except:
            pass
        await state.set_state(DealStates.waiting_deal_type)

    @dp.callback_query(DealStates.waiting_deal_type, F.data.startswith("type_"))
    async def deal_type_selected(callback: CallbackQuery, state: FSMContext):
        await callback.answer()

        type_key = callback.data.split("_")[1]
        type_map = {"gift": "Подарок", "account": "Аккаунт", "other": "Другое"}
        deal_type = type_map.get(type_key, "Другое")
        await state.update_data(deal_type=deal_type)

        text = f"<b>Введите описание товара</b> (Тип: {deal_type}):"
        if deal_type == "Подарок":
            text += "\n\n<i>ВНИМАНИЕ! Для типа 'Подарок':\nПосле подтверждения оплаты вы должны передать подарок покупателю.</i>"

        await callback.message.edit_text(
            text, parse_mode="HTML", reply_markup=back_menu()
        )
        await state.set_state(DealStates.waiting_description)

    @dp.message(DealStates.waiting_description, F.text)
    async def get_description(message: Message, state: FSMContext):
        await state.update_data(description=message.text)
        await message.answer(
            "<b>Введите сумму сделки:</b>\nПример: 15000",
            parse_mode="HTML",
            reply_markup=back_menu(),
        )
        await state.set_state(DealStates.waiting_amount)

    @dp.message(DealStates.waiting_amount, F.text)
    async def get_amount(message: Message, state: FSMContext):
        try:
            amount = float(message.text.replace(",", "."))
            if amount <= 0:
                raise ValueError
        except:
            await message.answer(
                "❌ Введите корректную сумму (положительное число):",
                reply_markup=back_menu(),
            )
            return

        await state.update_data(amount=amount)
        await message.answer(
            f"<b>Выберите валюту для суммы {format_amount(amount)}:</b>",
            parse_mode="HTML",
            reply_markup=currency_menu(),
        )
        await state.set_state(DealStates.waiting_currency)

    @dp.callback_query(DealStates.waiting_currency, F.data.startswith("cur_"))
    async def get_currency(callback: CallbackQuery, state: FSMContext):
        await callback.answer()

        currency = callback.data.split("_")[1]
        data = await state.get_data()

        deal_type = data.get("deal_type")
        description = data.get("description")
        amount = data.get("amount")

        user_id = callback.from_user.id

        deal_id = db.create_deal(user_id, deal_type, description, amount, currency)
        link = f"https://t.me/{BOT_USERNAME}?start=deal_{deal_id}"
        amount_str = format_amount(amount)

        text = f"""
✅ <b>Сделка успешно создана!</b>

<b>Тип:</b> {deal_type}
<b>Товар:</b> {description}
<b>Сумма:</b> {amount_str} {currency}

<b>ID сделки:</b> {deal_id}

---

<b>Ссылка для покупателя:</b>
<code>{link}</code>

⚠️ <b>Передавайте товар только после получения уведомления об оплате!</b>
"""
        if deal_type == "Подарок":
            text += "\n\n<i>ВНИМАНИЕ! Для типа 'Подарок':\nПосле подтверждения оплаты вы должны передать подарок покупателю.</i>"

        await callback.message.edit_text(
            text, parse_mode="HTML", reply_markup=back_menu()
        )
        await state.clear()

    @dp.callback_query(DealStates.waiting_currency, F.data == "back_to_deal_type")
    async def back_to_deal_type(callback: CallbackQuery, state: FSMContext):
        await callback.answer()
        await callback.message.edit_text(
            "Выберите тип сделки:", reply_markup=deal_type_menu()
        )
        await state.set_state(DealStates.waiting_deal_type)

    # ==================== РЕКВИЗИТЫ ====================

    @dp.callback_query(F.data == "requisites")
    async def requisites_handler(callback: CallbackQuery):
        user_data = db.get_user(callback.from_user.id)
        requisites = json.loads(user_data[8]) if user_data and user_data[8] else {}

        text = "💳 <b>Ваши реквизиты для вывода:</b>\n\n"
        type_names = {
            "card": "Карта",
            "kaspi": "Kaspi",
            "qiwi": "QIWI",
            "yoomoney": "ЮMoney",
            "webmoney": "WebMoney",
        }

        for req_type, name in type_names.items():
            val = requisites.get(req_type, "<i>не указано</i>")
            text += f"• <b>{name}:</b> {val}\n"

        text += "\nВыберите тип для изменения:"
        await callback.answer()
        await callback.message.answer(
            text, parse_mode="HTML", reply_markup=requisites_edit_menu()
        )
        try:
            await callback.message.delete()
        except:
            pass

    @dp.callback_query(F.data == "scam_base")
    async def scam_base_handler(callback: CallbackQuery):
        await callback.answer()
        await callback.message.answer(
            "Выберите действие:", reply_markup=scam_base_menu()
        )
        try:
            await callback.message.delete()
        except:
            pass

    @dp.callback_query(F.data == "my_deals")
    async def my_deals_handler(callback: CallbackQuery):
        deals = db.get_user_deals(callback.from_user.id)
        if not deals:
            await callback.answer()
            await callback.message.answer(
                "📋 <b>У вас пока нет сделок</b>",
                parse_mode="HTML",
                reply_markup=back_menu(),
            )
            try:
                await callback.message.delete()
            except:
                pass
            return

        text = "📋 <b>Ваши последние сделки:</b>\n\n"
        for deal in deals[:10]:
            status_emoji = "⏳" if deal[7] == "waiting" else "✅"
            text += f"{status_emoji} #{deal[0]} | {deal[3]} | {format_amount(deal[5])} {deal[6]}\n"

        await callback.answer()
        await callback.message.answer(
            text, parse_mode="HTML", reply_markup=back_menu()
        )
        try:
            await callback.message.delete()
        except:
            pass

    @dp.callback_query(F.data == "withdraw")
    async def withdraw_handler(callback: CallbackQuery):
        user_data = db.get_user(callback.from_user.id)
        available = user_data[3] if user_data else 0

        text = f"""
💰 <b>Вывод средств</b>

<b>Доступно для вывода:</b> {format_amount(available)} RUB
<b>Минимальная сумма:</b> 100 RUB

Для вывода средств у вас должны быть заполнены реквизиты.
"""
        await callback.answer()
        await callback.message.answer(
            text, parse_mode="HTML", reply_markup=back_menu()
        )
        try:
            await callback.message.delete()
        except:
            pass
        if available > 0:
            await callback.message.answer(
                f"💰 <b>Доступно для вывода:</b> {format_amount(available)} RUB\n\nВведите сумму для вывода:",
                parse_mode="HTML",
            )

    @dp.callback_query(F.data.startswith("req_"))
    async def requisites_edit_start(callback: CallbackQuery, state: FSMContext):
        await callback.answer()

        req_type = callback.data[4:]
        type_names = {
            "card": "Карта",
            "kaspi": "Kaspi",
            "qiwi": "QIWI",
            "yoomoney": "ЮMoney",
            "webmoney": "WebMoney",
        }

        await state.update_data(req_type=req_type)
        await callback.message.edit_text(
            f"<b>{type_names[req_type]}</b>\n\nВведите реквизиты:\n\nПример: 2200 7000 8000 5500",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ Назад", callback_data="requisites")]
                ]
            ),
        )
        await state.set_state(RequisitesStates.waiting_value)

    @dp.message(RequisitesStates.waiting_value, F.text)
    async def get_requisite_value(message: Message, state: FSMContext):
        data = await state.get_data()
        req_type = data.get("req_type")

        if not req_type:
            await message.answer("❌ Ошибка! Попробуйте снова.")
            await state.clear()
            return

        value = message.text
        db.update_requisites(message.from_user.id, req_type, value)

        type_names = {
            "card": "Карта",
            "kaspi": "Kaspi",
            "qiwi": "QIWI",
            "yoomoney": "ЮMoney",
            "webmoney": "WebMoney",
        }

        await message.answer(
            f"✅ {type_names.get(req_type, req_type)} сохранена!",
            parse_mode="HTML",
            reply_markup=back_to_requisites(),
        )
        await state.clear()

    # ==================== СКАМ БАЗА ====================

    @dp.callback_query(F.data == "scam_base")
    async def scam_base_menu_handler(callback: CallbackQuery):
        await callback.answer()
        await callback.message.edit_text(
            "Выберите действие:", reply_markup=scam_base_menu()
        )

    @dp.callback_query(F.data == "check_user")
    async def check_user_start(callback: CallbackQuery, state: FSMContext):
        await callback.answer()
        await callback.message.edit_text(
            "🔍 <b>Проверка пользователя</b>\n\nВведите @username пользователя для проверки:",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ Назад", callback_data="scam_base")]
                ]
            ),
        )
        await state.set_state(ScamStates.waiting_username)

    @dp.callback_query(F.data == "report_scam")
    async def report_scam_start(callback: CallbackQuery, state: FSMContext):
        await callback.answer()
        await callback.message.edit_text(
            "🚨 <b>Сообщить о скамере</b>\n\nВведите @username пользователя, которого хотите сообщить как скамера:",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ Назад", callback_data="scam_base")]
                ]
            ),
        )
        await state.set_state(ScamStates.waiting_username)

    @dp.message(ScamStates.waiting_username, F.text)
    async def get_scam_username(message: Message, state: FSMContext, bot: Bot):
        username = message.text

        await message.answer(
            f"✅ Сообщение о пользователе {username} отправлено администрации.\n\nСпасибо за бдительность!",
            parse_mode="HTML",
            reply_markup=back_menu(),
        )

        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(
                    admin_id,
                    f"🚨 Жалоба на скамера: {username}\nОт: {message.from_user.first_name} @{message.from_user.username}",
                )
            except:
                pass

        await state.clear()

    # ==================== ПРОЧИЕ ОБРАБОТЧИКИ ====================

    @dp.callback_query(F.data == "my_deals")
    async def my_deals_handler(callback: CallbackQuery):
        await callback.answer()

        deals = db.get_user_deals(callback.from_user.id)
        if not deals:
            await callback.message.edit_text(
                "📋 <b>У вас пока нет сделок</b>",
                parse_mode="HTML",
                reply_markup=back_menu(),
            )
        else:
            text = "📋 <b>Мои сделки</b>\n\n"
            for d in deals:
                status_emoji = "✅" if d[7] == "paid" else "🟡"
                status_text = "Завершена" if d[7] == "paid" else "Ожидает оплаты"
                text += f"{status_emoji} <b>Сделка #{d[0]}</b>\n"
                text += f"   📦 {d[3]}\n"
                text += f"   💰 {format_amount(d[5])} {d[6]}\n"
                text += f"   📅 {d[8][:10]}\n"
                text += f"   📌 {status_text}\n\n"

            await callback.message.edit_text(
                text, parse_mode="HTML", reply_markup=back_menu()
            )

    @dp.callback_query(F.data == "profile")
    async def profile_handler(callback: CallbackQuery):
        await callback.answer()

        user = db.get_user(callback.from_user.id)
        reqs = json.loads(user[8]) if user and user[8] else {}
        rating = user[7] if user else 5.0
        deals_count = user[5] if user else 0

        text = f"""
<b>👤 Профиль: {callback.from_user.first_name}</b>
<b>Рейтинг:</b> {get_rating_stars(rating)} ({rating:.1f}/5) | <b>Сделок:</b> {deals_count}

<b>🆔 ID</b>
Ваш ID: <code>{callback.from_user.id}</code>

<b>💰 Баланс:</b> {format_amount(user[3] if user else 0)} RUB
<b>🔒 Заморожено:</b> {format_amount(user[4] if user else 0)} RUB
<b>💵 Доступно:</b> {format_amount((user[3] if user else 0) - (user[4] if user else 0))} RUB

<b>📌 Реквизиты:</b>
- 💳 Карта: {reqs.get("card", "Не указан")}
- 🇰🇿 Kaspi: {reqs.get("kaspi", "Не указан")}
- 💸 QIWI: {reqs.get("qiwi", "Не указан")}
- 💰 ЮMoney: {reqs.get("yoomoney", "Не указан")}
- 🌐 WebMoney: {reqs.get("webmoney", "Не указан")}

<b>📊 Статистика сделок:</b>
- 📈 Продажи: {user[5] if user else 0} завершённых
- 📉 Покупки: {user[6] if user else 0} завершённых

💡 <b>Вывод средств:</b>
Вывод средств доступен только с доступного баланса
"""
        await callback.message.edit_text(
            text, parse_mode="HTML", reply_markup=back_menu()
        )

    @dp.callback_query(F.data == "withdraw")
    async def withdraw_start(callback: CallbackQuery, state: FSMContext):
        await callback.answer()

        user = db.get_user(callback.from_user.id)
        available = (user[3] if user else 0) - (user[4] if user else 0)

        if available > 0:
            await callback.message.edit_text(
                f"💰 <b>Доступно для вывода:</b> {format_amount(available)} RUB\n\nВведите сумму для вывода:",
                parse_mode="HTML",
                reply_markup=back_menu(),
            )
            await state.set_state(WithdrawStates.waiting_amount)
        else:
            text = f"""
<b>❌ Недостаточно доступных средств</b>

Часть средств заморожена в активных сделках

<b>💰 Баланс:</b> {format_amount(user[3] if user else 0)} RUB
<b>🔒 Заморожено:</b> {format_amount(user[4] if user else 0)} RUB
<b>💵 Доступно:</b> {format_amount(available)} RUB
"""
            await callback.message.edit_text(
                text, parse_mode="HTML", reply_markup=back_menu()
            )

    @dp.message(WithdrawStates.waiting_amount, F.text)
    async def withdraw_amount(message: Message, state: FSMContext):
        try:
            amount = float(message.text.replace(",", "."))
            if amount <= 0:
                raise ValueError
        except:
            await message.answer(
                "❌ Введите корректную сумму:", reply_markup=back_menu()
            )
            return

        # Здесь логика вывода
        await message.answer(
            f"✅ Заявка на вывод {format_amount(amount)} RUB отправлена администрации!",
            parse_mode="HTML",
            reply_markup=back_menu(),
        )
        await state.clear()

    @dp.callback_query(F.data.startswith("pay_"))
    async def pay_deal_handler(callback: CallbackQuery, bot: Bot):
        await callback.answer()

        deal_id = callback.data.replace("pay_", "")
        deal = db.get_deal(deal_id)

        if deal and deal["status"] == "waiting":
            db.mark_paid(deal_id)
            amount_str = format_amount(deal["amount"])

            await callback.message.edit_text(
                f"✅ <b>Оплата по сделке #{deal_id} отмечена!</b>",
                parse_mode="HTML",
                reply_markup=back_menu(),
            )

            await bot.send_message(
                deal["seller_id"],
                f"💰 <b>Покупатель оплатил сделку #{deal_id}</b>\n\n"
                f"📦 <b>Тип:</b> {deal['deal_type']}\n"
                f"📋 <b>Товар:</b> {deal['description']}\n"
                f"💵 <b>Сумма:</b> +{amount_str} 💸 {deal['currency']}\n\n"
                f"👤 <b>Покупатель:</b> ID {callback.from_user.id}\n\n"
                f"<i>✅ Деньги поступили. Можете передавать товар/подарок.</i>\n\n"
                f"🎁 <b>ИНСТРУКЦИЯ ПО ПЕРЕДАЧЕ ПОДАРКА</b>\n\n"
                f"1. 📦 Передайте подарок гаранту: @garantmoskow\n"
                f"2. ✅ Передача подтвержаеся автоматически\n"
                f"3. 💰 После подтверждения средства будут зачислены на ваш баланс",
                parse_mode="HTML",
                reply_markup=back_menu(),
            )
    @dp.callback_query(F.data == "menu")
    async def menu_handler(callback: CallbackQuery):
        await callback.answer()
        await send_main_menu(
            callback,
            callback.from_user.id,
            callback.from_user.username,
            callback.from_user.first_name,
        )
    @dp.callback_query(F.data == "back_to_menu")
    async def back_to_menu_handler(callback: CallbackQuery):
        await callback.answer()
        await send_main_menu(
            callback.message,
            callback.from_user.id,
            callback.from_user.username,
            callback.from_user.first_name,
        )
        try:
            await callback.message.delete()
        except:
            pass


# ==================== ЗАПУСК ====================


async def main():
    bot = Bot(token=BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Регистрируем все обработчики
    register_handlers(dp)

    print("✅ GIFT GUARD бот запущен!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
    asyncio.run(main())
