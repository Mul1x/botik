from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from config import MAIN_ADMIN_ID, WAITING_ADMIN_USERNAME
from database import is_admin, get_admins, add_admin, remove_admin
from utils.video import edit_menu_with_video


async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Панель администратора"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.callback_query.answer("У вас нет доступа!", show_alert=True)
        return
    
    admins = get_admins()
    admins_list = "\n".join([f"• `{a['user_id']}` @{a['username']}" for a in admins])
    
    keyboard = [
        [InlineKeyboardButton("➕ Добавить админа", callback_data="admin_add")],
        [InlineKeyboardButton("❌ Удалить админа", callback_data="admin_remove")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = (
        f"👑 *Админ панель*\n\n"
        f"*Список администраторов:*\n{admins_list}\n\n"
        f"Выберите действие:"
    )
    
    await edit_menu_with_video(update.callback_query, text, reply_markup)


async def admin_add_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало добавления админа"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [[InlineKeyboardButton("🔙 Отмена", callback_data="admin_panel")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "➕ *Добавление администратора*\n\nВведите username пользователя (без @):",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    
    return WAITING_ADMIN_USERNAME


async def admin_add_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение username для добавления админа"""
    username = update.message.text.strip().replace("@", "")
    admin_id = update.effective_user.id
    
    # Пытаемся получить user_id по username
    try:
        chat = await context.bot.get_chat(f"@{username}")
        user_id = chat.id
    except Exception:
        await update.message.reply_text(
            "❌ Пользователь не найден. Убедитесь, что username введен правильно.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]])
        )
        return WAITING_ADMIN_USERNAME
    
    add_admin(user_id, username, admin_id)
    
    keyboard = [[InlineKeyboardButton("🔙 В админ панель", callback_data="admin_panel")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"✅ Администратор @{username} успешно добавлен!",
        reply_markup=reply_markup
    )
    
    return ConversationHandler.END


async def admin_remove_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало удаления админа"""
    query = update.callback_query
    await query.answer()
    
    admins = get_admins()
    keyboard = []
    
    for admin in admins:
        if admin['user_id'] != MAIN_ADMIN_ID:
            keyboard.append([
                InlineKeyboardButton(
                    f"❌ {admin['username']} ({admin['user_id']})",
                    callback_data=f"admin_remove_{admin['user_id']}"
                )
            ])
    
    keyboard.append([InlineKeyboardButton("🔙 Отмена", callback_data="admin_panel")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "❌ *Удаление администратора*\n\nВыберите админа для удаления:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )


async def admin_remove_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id_to_remove: int):
    """Подтверждение удаления админа"""
    query = update.callback_query
    
    if user_id_to_remove == MAIN_ADMIN_ID:
        await query.answer("Нельзя удалить главного администратора!", show_alert=True)
        return
    
    if remove_admin(user_id_to_remove):
        await query.answer("Администратор удален!")
    else:
        await query.answer("Ошибка при удалении!")
    
    await admin_panel(update, context)


async def confirm_payment(update: Update, context: ContextTypes.DEFAULT_TYPE, deal_id: str):
    """Админ подтверждает оплату"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.callback_query.answer("У вас нет прав для подтверждения оплаты!", show_alert=True)
        return
    
    from database import get_deal, update_deal_status
    
    deal = get_deal(deal_id)
    if not deal:
        await update.callback_query.answer("Сделка не найдена!")
        return
    
    update_deal_status(deal_id, "paid")
    
    # Уведомляем продавца
    try:
        await context.bot.send_message(
            deal['seller_id'],
            f"✅ *Оплата подтверждена!*\n\n"
            f"Сделка #{deal_id}\n"
            f"Сумма: {deal['amount_rub']} RUB\n\n"
            f"Можете передать товар покупателю.\n"
            f"После передачи нажмите /complete_{deal_id}",
            parse_mode="Markdown"
        )
    except Exception:
        pass
    
    # Уведомляем покупателя
    if deal.get('buyer_id'):
        try:
            await context.bot.send_message(
                deal['buyer_id'],
                f"✅ *Оплата подтверждена!*\n\n"
                f"Сделка #{deal_id}\n"
                f"Продавец получил уведомление. Ожидайте передачи товара.",
                parse_mode="Markdown"
            )
        except Exception:
            pass
    
    await update.callback_query.answer("Оплата подтверждена!")
    await update.callback_query.edit_message_reply_markup(reply_markup=None)
