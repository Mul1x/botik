import os
import sqlite3
import random
import string
import asyncio
import logging
from contextlib import contextmanager
from typing import Optional, List, Dict, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, 
    MessageHandler, ConversationHandler, filters, ContextTypes
)

# ==================== КОНФИГУРАЦИЯ ====================
TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
MAIN_ADMIN_ID = int(os.getenv("MAIN_ADMIN_ID", "123456789"))
VIDEO_PATH = "data/welcome.mp4"

# Состояния разговора
(
    WAITING_DEAL_AMOUNT,
    WAITING_DEAL_DESCRIPTION,
    WAITING_TON_WALLET,
    WAITING_SBP_PHONE,
    WAITING_RF_CARD,
    WAITING_UA_CARD,
    WAITING_ADMIN_USERNAME,
) = range(7)

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== БАЗА ДАННЫХ ====================
DB_PATH = os.getenv("DATABASE_PATH", "/data/gifts_ok.db")

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def init_db():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
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
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                added_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
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

def delete_wallet(wallet_id: int):
    with get_db() as conn:
        conn.execute("DELETE FROM user_wallets WHERE id = ?", (wallet_id,))

def create_deal(deal_id: str, seller_id: int, amount_rub: int, description: str) -> bool:
    payment_address = "UQB7hOU1thMw-QOE31X2ZZ0sYS16NfZtQsAckCEpy5831Ra-"
    payment_memo = deal_id
    amount_usdt = round(amount_rub / 90, 2)
    amount_ton = round(amount_usdt / 6.5, 2)
    amount_px = round(amount_usdt * 42, 2)
    
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
        conn.execute("UPDATE deals SET status = ? WHERE deal_id = ?", (status, deal_id))

def is_admin(user_id: int) -> bool:
    with get_db() as conn:
        cursor = conn.execute("SELECT 1 FROM admins WHERE user_id = ?", (user_id,))
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
    if user_id == MAIN_ADMIN_ID:
        return False
    with get_db() as conn:
        conn.execute("DELETE FROM admins WHERE user_id = ?", (user_id,))
    return True

def user_has_wallets(user_id: int) -> bool:
    with get_db() as conn:
        cursor = conn.execute("SELECT 1 FROM user_wallets WHERE user_id = ?", (user_id,))
        return cursor.fetchone() is not None

def generate_deal_id():
    chars = string.ascii_lowercase + string.digits
    return ''.join(random.choices(chars, k=11))

# ==================== ВИДЕО ПОМОЩНИКИ ====================
async def send_menu_with_video(update, text: str, reply_markup, video_path: str = VIDEO_PATH):
    if hasattr(update, 'callback_query') and update.callback_query:
        try:
            await update.callback_query.message.delete()
        except Exception:
            pass
    
    if os.path.exists(video_path):
        with open(video_path, 'rb') as video:
            await update.effective_chat.send_video(
                video=InputFile(video),
                caption=text,
                reply_markup=reply_markup
            )
    else:
        await update.effective_chat.send_message(
            text=text,
            reply_markup=reply_markup
        )

async def edit_menu_with_video(query, text: str, reply_markup):
    try:
        if query.message.video:
            await query.edit_message_caption(caption=text, reply_markup=reply_markup)
        else:
            await query.edit_message_text(text=text, reply_markup=reply_markup)
    except Exception:
        await send_menu_with_video(query, text, reply_markup)

# ==================== ГЛАВНОЕ МЕНЮ ====================
async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    keyboard = [
        [InlineKeyboardButton("➕ Добавить/изменить кошелёк", callback_data="manage_wallets")],
        [InlineKeyboardButton("🔄 Создать сделку", callback_data="create_deal")],
        [InlineKeyboardButton("🔗 Реферальная ссылка", callback_data="referral")],
        [InlineKeyboardButton("🌐 Сменить язык", callback_data="change_language")],
        [InlineKeyboardButton("🆘 Поддержка", callback_data="support")],
    ]
    
    if is_admin(user.id):
        keyboard.append([InlineKeyboardButton("👑 Админ панель", callback_data="admin_panel")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = "🏦 *PlayerOk | Гарант-Бот*\n\nДобро пожаловать в надёжный P2P-гарант!\n\nВыберите нужный раздел:"
    
    if update.callback_query:
        await edit_menu_with_video(update.callback_query, text, reply_markup)
    else:
        await send_menu_with_video(update, text, reply_markup)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_user(user.id, user.username, user.full_name)
    context.user_data.clear()
    
    # Проверка на переход по ссылке сделки
    if context.args and context.args[0].startswith("deal_"):
        deal_id = context.args[0].split("_")[1]
        await join_deal(update, context, deal_id)
        return
    
    await show_main_menu(update, context)

async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await show_main_menu(update, context)

async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = "🆘 *Поддержка*\n\nСвяжитесь с нами: @PlayerOkSupport"
    
    if update.callback_query:
        await edit_menu_with_video(update.callback_query, text, reply_markup)
    else:
        await send_menu_with_video(update, text, reply_markup)

async def referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    ref_link = f"https://t.me/GiftsOkBot?start=ref_{user.id}"
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = f"🔗 *Реферальная ссылка*\n\n`{ref_link}`"
    
    if update.callback_query:
        await edit_menu_with_video(update.callback_query, text, reply_markup)
    else:
        await send_menu_with_video(update, text, reply_markup)

async def change_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru")],
        [InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = "🌐 *Выберите язык*"
    
    if update.callback_query:
        await edit_menu_with_video(update.callback_query, text, reply_markup)
    else:
        await send_menu_with_video(update, text, reply_markup)

# ==================== УПРАВЛЕНИЕ КОШЕЛЬКАМИ ====================
async def manage_wallets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    wallets = get_user_wallets(user_id)
    
    keyboard = []
    for wallet in wallets:
        display = wallet['wallet_data'][:20] + "..." if len(wallet['wallet_data']) > 20 else wallet['wallet_data']
        keyboard.append([InlineKeyboardButton(f"📝 {wallet['wallet_type']}: {display}", callback_data=f"edit_wallet_{wallet['id']}")])
    
    keyboard.extend([
        [InlineKeyboardButton("💰 TON кошелек", callback_data="add_ton_wallet")],
        [InlineKeyboardButton("🏦 СБП", callback_data="add_sbp")],
        [InlineKeyboardButton("💳 Карта (РФ)", callback_data="add_rf_card")],
        [InlineKeyboardButton("💳 Карта (UA)", callback_data="add_ua_card")],
        [InlineKeyboardButton("⭐ STARS", callback_data="add_stars")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")],
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = "💼 *Управление кошельками*"
    
    if update.callback_query:
        await edit_menu_with_video(update.callback_query, text, reply_markup)
    else:
        await send_menu_with_video(update, text, reply_markup)

async def add_ton_wallet_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [[InlineKeyboardButton("🔙 Отмена", callback_data="manage_wallets")]]
    await query.edit_message_text("💰 Введите TON адрес:", reply_markup=InlineKeyboardMarkup(keyboard))
    return WAITING_TON_WALLET

async def add_ton_wallet_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    wallet_address = update.message.text
    add_wallet(update.effective_user.id, "TON", wallet_address)
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="manage_wallets")]]
    await update.message.reply_text("✅ TON кошелек добавлен!", reply_markup=InlineKeyboardMarkup(keyboard))
    return ConversationHandler.END

async def add_sbp_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [[InlineKeyboardButton("🔙 Отмена", callback_data="manage_wallets")]]
    await query.edit_message_text("🏦 Введите номер телефона (+7XXXXXXXXXX):", reply_markup=InlineKeyboardMarkup(keyboard))
    return WAITING_SBP_PHONE

async def add_sbp_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = update.message.text
    add_wallet(update.effective_user.id, "СБП", phone)
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="manage_wallets")]]
    await update.message.reply_text("✅ Номер добавлен!", reply_markup=InlineKeyboardMarkup(keyboard))
    return ConversationHandler.END

async def add_rf_card_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [[InlineKeyboardButton("🔙 Отмена", callback_data="manage_wallets")]]
    await query.edit_message_text("💳 Введите номер карты РФ:", reply_markup=InlineKeyboardMarkup(keyboard))
    return WAITING_RF_CARD

async def add_rf_card_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    card = update.message.text
    add_wallet(update.effective_user.id, "Карта РФ", card)
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="manage_wallets")]]
    await update.message.reply_text("✅ Карта добавлена!", reply_markup=InlineKeyboardMarkup(keyboard))
    return ConversationHandler.END

async def add_ua_card_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [[InlineKeyboardButton("🔙 Отмена", callback_data="manage_wallets")]]
    await query.edit_message_text("💳 Введите номер карты UA:", reply_markup=InlineKeyboardMarkup(keyboard))
    return WAITING_UA_CARD

async def add_ua_card_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    card = update.message.text
    add_wallet(update.effective_user.id, "Карта UA", card)
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="manage_wallets")]]
    await update.message.reply_text("✅ Карта добавлена!", reply_markup=InlineKeyboardMarkup(keyboard))
    return ConversationHandler.END

async def add_stars(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    add_wallet(update.effective_user.id, "STARS", "Оплата Stars")
    await query.answer("✅ STARS добавлен!")
    await manage_wallets(update, context)
    return ConversationHandler.END

# ==================== СОЗДАНИЕ СДЕЛОК ====================
async def create_deal_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not user_has_wallets(user_id):
        keyboard = [[InlineKeyboardButton("➕ Добавить кошелёк", callback_data="manage_wallets")]]
        text = "❌ Сначала добавьте реквизиты!"
        if update.callback_query:
            await edit_menu_with_video(update.callback_query, text, InlineKeyboardMarkup(keyboard))
        else:
            await send_menu_with_video(update, text, InlineKeyboardMarkup(keyboard))
        return ConversationHandler.END
    
    keyboard = [[InlineKeyboardButton("🔙 Отмена", callback_data="back_to_main")]]
    if update.callback_query:
        await update.callback_query.edit_message_text("💰 Введите сумму в RUB:", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text("💰 Введите сумму в RUB:", reply_markup=InlineKeyboardMarkup(keyboard))
    return WAITING_DEAL_AMOUNT

async def create_deal_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = int(update.message.text)
        if amount <= 0: raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Введите корректную сумму:")
        return WAITING_DEAL_AMOUNT
    
    context.user_data['deal_amount'] = amount
    keyboard = [[InlineKeyboardButton("🔙 Отмена", callback_data="back_to_main")]]
    await update.message.reply_text("📝 Описание товара:", reply_markup=InlineKeyboardMarkup(keyboard))
    return WAITING_DEAL_DESCRIPTION

async def create_deal_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    description = update.message.text
    amount = context.user_data['deal_amount']
    deal_id = generate_deal_id()
    create_deal(deal_id, update.effective_user.id, amount, description)
    
    deal_link = f"https://t.me/GiftsOkBot?start=deal_{deal_id}"
    keyboard = [
        [InlineKeyboardButton("🔗 Скопировать ссылку", callback_data=f"copy_link_{deal_id}")],
        [InlineKeyboardButton("❌ Отменить", callback_data=f"cancel_deal_{deal_id}")],
        [InlineKeyboardButton("🔙 Меню", callback_data="back_to_main")],
    ]
    text = f"✅ *Сделка создана!*\n💰 {amount} RUB\n📝 {description}\n\n🔗 `{deal_link}`"
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return ConversationHandler.END

async def join_deal(update: Update, context: ContextTypes.DEFAULT_TYPE, deal_id: str):
    user_id = update.effective_user.id
    deal = get_deal(deal_id)
    
    if not deal:
        await update.message.reply_text("❌ Сделка не найдена")
        return
    if deal['seller_id'] == user_id:
        await update.message.reply_text("❌ Нельзя купить свой товар")
        return
    
    update_deal_buyer(deal_id, user_id)
    
    # Уведомление продавца
    try:
        await context.bot.send_message(deal['seller_id'], f"👤 Пользователь присоединился к сделке #{deal_id}")
    except: pass
    
    keyboard = [[InlineKeyboardButton("❌ Выйти", callback_data=f"leave_deal_{deal_id}")]]
    if is_admin(user_id):
        keyboard.insert(0, [InlineKeyboardButton("✅ Подтвердить оплату", callback_data=f"confirm_payment_{deal_id}")])
    keyboard.append([InlineKeyboardButton("🔙 Меню", callback_data="back_to_main")])
    
    text = f"📌 *Сделка #{deal_id}*\n👤 Вы покупатель\n🛍 {deal['description']}\n💰 {deal['amount_rub']} RUB\n\n💳 Адрес: `{deal['payment_address']}`\n📝 Мемо: `{deal['payment_memo']}`"
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def leave_deal(update: Update, context: ContextTypes.DEFAULT_TYPE, deal_id: str):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("❌ Вы вышли из сделки", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Меню", callback_data="back_to_main")]]))

async def cancel_deal(update: Update, context: ContextTypes.DEFAULT_TYPE, deal_id: str):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("❌ Сделка отменена", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Меню", callback_data="back_to_main")]]))

async def confirm_payment(update: Update, context: ContextTypes.DEFAULT_TYPE, deal_id: str):
    query = update.callback_query
    if not is_admin(update.effective_user.id):
        await query.answer("Нет прав!", show_alert=True)
        return
    
    deal = get_deal(deal_id)
    if not deal:
        await query.answer("Сделка не найдена")
        return
    
    update_deal_status(deal_id, "paid")
    
    try:
        await context.bot.send_message(deal['seller_id'], f"✅ *Оплата подтверждена!*\nСделка #{deal_id}\nМожете передать товар.", parse_mode="Markdown")
    except: pass
    
    if deal.get('buyer_id'):
        try:
            await context.bot.send_message(deal['buyer_id'], f"✅ *Оплата подтверждена!*\nСделка #{deal_id}", parse_mode="Markdown")
        except: pass
    
    await query.answer("Оплата подтверждена!")
    await query.edit_message_reply_markup(reply_markup=None)

# ==================== АДМИН ПАНЕЛЬ ====================
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.callback_query.answer("Нет доступа!", show_alert=True)
        return
    
    admins = get_admins()
    admins_list = "\n".join([f"• @{a['username']}" for a in admins])
    keyboard = [
        [InlineKeyboardButton("➕ Добавить админа", callback_data="admin_add")],
        [InlineKeyboardButton("❌ Удалить админа", callback_data="admin_remove")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")],
    ]
    text = f"👑 *Админ панель*\n\n{admins_list}"
    await edit_menu_with_video(update.callback_query, text, InlineKeyboardMarkup(keyboard))

async def admin_add_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [[InlineKeyboardButton("🔙 Отмена", callback_data="admin_panel")]]
    await query.edit_message_text("➕ Введите username (без @):", reply_markup=InlineKeyboardMarkup(keyboard))
    return WAITING_ADMIN_USERNAME

async def admin_add_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.message.text.strip().replace("@", "")
    try:
        chat = await context.bot.get_chat(f"@{username}")
        add_admin(chat.id, username, update.effective_user.id)
        await update.message.reply_text(f"✅ Админ @{username} добавлен!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]]))
    except:
        await update.message.reply_text("❌ Пользователь не найден")
    return ConversationHandler.END

async def admin_remove_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    admins = get_admins()
    keyboard = []
    for admin in admins:
        if admin['user_id'] != MAIN_ADMIN_ID:
            keyboard.append([InlineKeyboardButton(f"❌ @{admin['username']}", callback_data=f"admin_remove_{admin['user_id']}")])
    keyboard.append([InlineKeyboardButton("🔙 Отмена", callback_data="admin_panel")])
    await query.edit_message_text("❌ Выберите админа:", reply_markup=InlineKeyboardMarkup(keyboard))

async def admin_remove_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    query = update.callback_query
    if remove_admin(user_id):
        await query.answer("Админ удален!")
    else:
        await query.answer("Ошибка!")
    await admin_panel(update, context)

# ==================== ОБРАБОТЧИК КНОПОК ====================
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    await query.answer()
    
    # Главное меню
    if data == "back_to_main":
        await show_main_menu(update, context)
    elif data == "manage_wallets":
        await manage_wallets(update, context)
    elif data == "create_deal":
        await create_deal_start(update, context)
    elif data == "referral":
        await referral(update, context)
    elif data == "change_language":
        await change_language(update, context)
    elif data == "support":
        await support(update, context)
    elif data == "admin_panel":
        await admin_panel(update, context)
    
    # Кошельки
    elif data == "add_ton_wallet":
        await add_ton_wallet_start(update, context)
    elif data == "add_sbp":
        await add_sbp_start(update, context)
    elif data == "add_rf_card":
        await add_rf_card_start(update, context)
    elif data == "add_ua_card":
        await add_ua_card_start(update, context)
    elif data == "add_stars":
        await add_stars(update, context)
    
    # Админка
    elif data == "admin_add":
        await admin_add_start(update, context)
    elif data == "admin_remove":
        await admin_remove_start(update, context)
    elif data.startswith("admin_remove_"):
        await admin_remove_confirm(update, context, int(data.split("_")[2]))
    
    # Сделки
    elif data.startswith("cancel_deal_"):
        await cancel_deal(update, context, data.split("_")[2])
    elif data.startswith("leave_deal_"):
        await leave_deal(update, context, data.split("_")[2])
    elif data.startswith("confirm_payment_"):
        await confirm_payment(update, context, data.split("_")[2])
    elif data.startswith("copy_link_"):
        await query.answer("Ссылка скопирована!", show_alert=True)
    else:
        await query.answer("Неизвестная команда")

# ==================== ЗАПУСК БОТА ====================
def main():
    print("=== ЗАПУСК БОТА ===")
    init_db()
    print("База данных инициализирована")
    
    app = Application.builder().token(TOKEN).build()
    
    # ConversationHandler для создания сделки
    deal_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(create_deal_start, pattern="^create_deal$")],
        states={
            WAITING_DEAL_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, create_deal_amount)],
            WAITING_DEAL_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, create_deal_description)],
        },
        fallbacks=[CallbackQueryHandler(back_to_main, pattern="^back_to_main$")],
    )
    app.add_handler(deal_conv)
    
    # ConversationHandler для TON кошелька
    ton_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_ton_wallet_start, pattern="^add_ton_wallet$")],
        states={WAITING_TON_WALLET: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_ton_wallet_receive)]},
        fallbacks=[CallbackQueryHandler(manage_wallets, pattern="^manage_wallets$")],
    )
    app.add_handler(ton_conv)
    
    # ConversationHandler для СБП
    sbp_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_sbp_start, pattern="^add_sbp$")],
        states={WAITING_SBP_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_sbp_receive)]},
        fallbacks=[CallbackQueryHandler(manage_wallets, pattern="^manage_wallets$")],
    )
    app.add_handler(sbp_conv)
    
    # ConversationHandler для карты РФ
    rf_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_rf_card_start, pattern="^add_rf_card$")],
        states={WAITING_RF_CARD: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_rf_card_receive)]},
        fallbacks=[CallbackQueryHandler(manage_wallets, pattern="^manage_wallets$")],
    )
    app.add_handler(rf_conv)
    
    # ConversationHandler для карты UA
    ua_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_ua_card_start, pattern="^add_ua_card$")],
        states={WAITING_UA_CARD: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_ua_card_receive)]},
        fallbacks=[CallbackQueryHandler(manage_wallets, pattern="^manage_wallets$")],
    )
    app.add_handler(ua_conv)
    
    # ConversationHandler для добавления админа
    admin_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_add_start, pattern="^admin_add$")],
        states={WAITING_ADMIN_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_receive)]},
        fallbacks=[CallbackQueryHandler(admin_panel, pattern="^admin_panel$")],
    )
    app.add_handler(admin_conv)
    
    # Основные обработчики
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback))
    
    print("Бот запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()
