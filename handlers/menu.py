from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import is_admin
from utils.video import send_menu_with_video, edit_menu_with_video


async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает главное меню"""
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
    
    text = (
        "🏦 *PlayerOk | Гарант-Бот*\n\n"
        "Добро пожаловать в надёжный P2P-гарант!\n\n"
        "Выберите нужный раздел ниже:"
    )
    
    if update.callback_query:
        await edit_menu_with_video(update.callback_query, text, reply_markup)
    else:
        await send_menu_with_video(update, text, reply_markup)


async def back_to_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Возврат в главное меню"""
    context.user_data.clear()
    await show_main_menu(update, context)


async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик поддержки"""
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = (
        "🆘 *Поддержка*\n\n"
        "Если у вас возникли вопросы или проблемы:\n\n"
        "📧 Свяжитесь с нами: @PlayerOkSupport\n"
        "📖 Инструкция: https://telegra.ph/Instrukciya-PlayerOk-01-01\n\n"
        "Мы ответим в ближайшее время!"
    )
    
    if update.callback_query:
        await edit_menu_with_video(update.callback_query, text, reply_markup)
    else:
        await send_menu_with_video(update, text, reply_markup)


async def referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик реферальной системы"""
    user = update.effective_user
    ref_link = f"https://t.me/GiftsOkBot?start=ref_{user.id}"
    
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = (
        "🔗 *Реферальная программа*\n\n"
        "Приглашайте друзей и получайте бонусы!\n\n"
        f"Ваша реферальная ссылка:\n`{ref_link}`\n\n"
        "За каждого приглашенного друга вы получаете 5% от комиссии его сделок!"
    )
    
    if update.callback_query:
        await edit_menu_with_video(update.callback_query, text, reply_markup)
    else:
        await send_menu_with_video(update, text, reply_markup)


async def change_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик смены языка"""
    keyboard = [
        [InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru")],
        [InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = "🌐 *Выберите язык / Choose language*"
    
    if update.callback_query:
        await edit_menu_with_video(update.callback_query, text, reply_markup)
    else:
        await send_menu_with_video(update, text, reply_markup)
