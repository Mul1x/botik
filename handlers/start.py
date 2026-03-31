from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import add_user, init_db
from utils.video import send_menu_with_video


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    add_user(user.id, user.username, user.full_name)
    
    # Инициализируем состояние
    context.user_data.clear()
    
    # Главное меню
    keyboard = [
        [InlineKeyboardButton("➕ Добавить/изменить кошелёк", callback_data="manage_wallets")],
        [InlineKeyboardButton("🔄 Создать сделку", callback_data="create_deal")],
        [InlineKeyboardButton("🔗 Реферальная ссылка", callback_data="referral")],
        [InlineKeyboardButton("🌐 Сменить язык", callback_data="change_language")],
        [InlineKeyboardButton("🆘 Поддержка", callback_data="support")],
    ]
    
    # Если пользователь админ, добавляем кнопку админ-панели
    from database import is_admin
    if is_admin(user.id):
        keyboard.append([InlineKeyboardButton("👑 Админ панель", callback_data="admin_panel")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = (
        "🏦 *PlayerOk | Гарант-Бот*\n\n"
        "Добро пожаловать в надёжный P2P-гарант!\n\n"
        "🔹 *Покупайте и продавайте всё что угодно – безопасно!*\n"
        "🔹 Удобное управление кошельками\n"
        "🔹 Реферальная система\n\n"
        "Выберите нужный раздел ниже:"
    )
    
    await send_menu_with_video(update, text, reply_markup)
