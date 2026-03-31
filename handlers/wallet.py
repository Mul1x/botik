from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from config import (
    WAITING_TON_WALLET, WAITING_SBP_PHONE, WAITING_RF_CARD, WAITING_UA_CARD
)
from database import get_user_wallets, add_wallet, delete_wallet
from utils.video import edit_menu_with_video, send_menu_with_video


async def manage_wallets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Управление кошельками/реквизитами"""
    user_id = update.effective_user.id
    wallets = get_user_wallets(user_id)
    
    keyboard = []
    
    # Показываем текущие кошельки
    for wallet in wallets:
        wallet_type = wallet['wallet_type']
        wallet_data = wallet['wallet_data']
        display_data = wallet_data[:20] + "..." if len(wallet_data) > 20 else wallet_data
        keyboard.append([
            InlineKeyboardButton(
                f"📝 {wallet_type}: {display_data}",
                callback_data=f"edit_wallet_{wallet['id']}"
            )
        ])
    
    # Кнопки добавления
    keyboard.extend([
        [InlineKeyboardButton("💰 Добавить TON-кошелек", callback_data="add_ton_wallet")],
        [InlineKeyboardButton("🏦 Добавить СБП", callback_data="add_sbp")],
        [InlineKeyboardButton("💳 Добавить банковскую карту (РФ)", callback_data="add_rf_card")],
        [InlineKeyboardButton("💳 Добавить банковскую карту (UA)", callback_data="add_ua_card")],
        [InlineKeyboardButton("⭐ Оплата в STARS", callback_data="add_stars")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")],
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = "💼 *Управление кошельками*\n\nВыберите действие:"
    
    if update.callback_query:
        await edit_menu_with_video(update.callback_query, text, reply_markup)
    else:
        await send_menu_with_video(update, text, reply_markup)


async def add_ton_wallet_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало добавления TON кошелька"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [[InlineKeyboardButton("🔙 Отмена", callback_data="manage_wallets")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "💰 *Добавление TON-кошелька*\n\nПожалуйста, введите ваш TON адрес:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    
    return WAITING_TON_WALLET


async def add_ton_wallet_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение TON адреса"""
    wallet_address = update.message.text
    user_id = update.effective_user.id
    
    # Простая валидация TON адреса
    if not wallet_address.startswith("UQ") and not wallet_address.startswith("EQ"):
        await update.message.reply_text(
            "❌ Неверный формат TON адреса. Адрес должен начинаться с UQ или EQ.\nПопробуйте снова:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Отмена", callback_data="manage_wallets")]])
        )
        return WAITING_TON_WALLET
    
    add_wallet(user_id, "TON кошелек", wallet_address)
    
    keyboard = [[InlineKeyboardButton("🔙 Назад к кошелькам", callback_data="manage_wallets")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "✅ TON кошелек успешно добавлен!",
        reply_markup=reply_markup
    )
    
    return ConversationHandler.END


async def add_sbp_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало добавления СБП"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [[InlineKeyboardButton("🔙 Отмена", callback_data="manage_wallets")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🏦 *Добавление СБП*\n\nПожалуйста, введите номер телефона в формате:\n`+7(XXX)XXX-XX-XX`",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    
    return WAITING_SBP_PHONE


async def add_sbp_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение номера телефона для СБП"""
    phone = update.message.text
    user_id = update.effective_user.id
    
    add_wallet(user_id, "СБП", phone)
    
    keyboard = [[InlineKeyboardButton("🔙 Назад к кошелькам", callback_data="manage_wallets")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "✅ Номер телефона для СБП успешно добавлен!",
        reply_markup=reply_markup
    )
    
    return ConversationHandler.END


async def add_rf_card_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало добавления карты РФ"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [[InlineKeyboardButton("🔙 Отмена", callback_data="manage_wallets")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "💳 *Добавление банковской карты (РФ)*\n\nПожалуйста, введите номер карты:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    
    return WAITING_RF_CARD


async def add_rf_card_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение номера карты РФ"""
    card = update.message.text
    user_id = update.effective_user.id
    
    add_wallet(user_id, "Банковская карта (РФ)", card)
    
    keyboard = [[InlineKeyboardButton("🔙 Назад к кошелькам", callback_data="manage_wallets")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "✅ Банковская карта успешно добавлена!",
        reply_markup=reply_markup
    )
    
    return ConversationHandler.END


async def add_ua_card_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало добавления карты UA"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [[InlineKeyboardButton("🔙 Отмена", callback_data="manage_wallets")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "💳 *Добавление банковской карты (UA)*\n\nПожалуйста, введите номер карты:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    
    return WAITING_UA_CARD


async def add_ua_card_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение номера карты UA"""
    card = update.message.text
    user_id = update.effective_user.id
    
    add_wallet(user_id, "Банковская карта (UA)", card)
    
    keyboard = [[InlineKeyboardButton("🔙 Назад к кошелькам", callback_data="manage_wallets")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "✅ Банковская карта успешно добавлена!",
        reply_markup=reply_markup
    )
    
    return ConversationHandler.END


async def add_stars(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Добавление оплаты в STARS"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    add_wallet(user_id, "STARS", "Оплата в Stars")
    
    keyboard = [[InlineKeyboardButton("🔙 Назад к кошелькам", callback_data="manage_wallets")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "⭐ Оплата в STARS успешно добавлена!",
        reply_markup=reply_markup
    )
    
    return ConversationHandler.END
