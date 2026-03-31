import random
import string
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from config import WAITING_DEAL_AMOUNT, WAITING_DEAL_DESCRIPTION
from database import (
    get_user_wallets, create_deal, get_deal, update_deal_buyer,
    update_deal_status, user_has_wallets
)
from utils.video import edit_menu_with_video, send_menu_with_video


def generate_deal_id():
    """Генерация уникального ID сделки"""
    chars = string.ascii_lowercase + string.digits
    return ''.join(random.choices(chars, k=11))


async def create_deal_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало создания сделки"""
    user_id = update.effective_user.id
    
    # Проверяем наличие реквизитов
    if not user_has_wallets(user_id):
        keyboard = [
            [InlineKeyboardButton("➕ Добавить кошелёк", callback_data="manage_wallets")],
            [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = "❌ *Для создания сделки необходимо добавить реквизиты!*\n\nПожалуйста, сначала добавьте кошелек или карту для получения оплаты."
        
        if update.callback_query:
            await edit_menu_with_video(update.callback_query, text, reply_markup)
        else:
            await send_menu_with_video(update, text, reply_markup)
        return ConversationHandler.END
    
    keyboard = [[InlineKeyboardButton("🔙 Отмена", callback_data="back_to_main")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = "💰 *Создание сделки*\n\nВведите сумму в RUB (например: 5000):"
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            text,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            text,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    
    return WAITING_DEAL_AMOUNT


async def create_deal_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение суммы сделки"""
    try:
        amount = int(update.message.text)
        if amount <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text(
            "❌ Пожалуйста, введите корректную сумму (положительное число):",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Отмена", callback_data="back_to_main")]])
        )
        return WAITING_DEAL_AMOUNT
    
    context.user_data['deal_amount'] = amount
    
    keyboard = [[InlineKeyboardButton("🔙 Отмена", callback_data="back_to_main")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "📝 *Описание товара*\n\nУкажите, что вы предлагаете в этой сделке:\nПример: 10 Кепок и Пепе...",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    
    return WAITING_DEAL_DESCRIPTION


async def create_deal_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение описания и создание сделки"""
    description = update.message.text
    amount = context.user_data['deal_amount']
    seller_id = update.effective_user.id
    
    deal_id = generate_deal_id()
    create_deal(deal_id, seller_id, amount, description)
    
    # Ссылка для покупателя
    deal_link = f"https://t.me/GiftsOkBot?start=deal_{deal_id}"
    
    keyboard = [
        [InlineKeyboardButton("🔗 Скопировать ссылку", callback_data=f"copy_link_{deal_id}")],
        [InlineKeyboardButton("❌ Отменить сделку", callback_data=f"cancel_deal_{deal_id}")],
        [InlineKeyboardButton("🔙 Вернуться в меню", callback_data="back_to_main")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = (
        f"✅ *Сделка успешно создана!*\n\n"
        f"💰 Сумма: {amount} RUB\n"
        f"📝 Описание: {description}\n\n"
        f"🔗 Ссылка для покупателя:\n`{deal_link}`\n\n"
        f"📌 ID сделки: `{deal_id}`"
    )
    
    await update.message.reply_text(
        text,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    
    return ConversationHandler.END


async def join_deal(update: Update, context: ContextTypes.DEFAULT_TYPE, deal_id: str):
    """Покупатель присоединяется к сделке по ссылке"""
    user_id = update.effective_user.id
    user = update.effective_user
    
    deal = get_deal(deal_id)
    if not deal:
        await update.message.reply_text("❌ Сделка не найдена или уже завершена.")
        return
    
    # Проверяем, не продавец ли это
    if deal['seller_id'] == user_id:
        keyboard = [[InlineKeyboardButton("🔙 Вернуться в меню", callback_data="back_to_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "❌ Вы не можете купить свой собственный товар!",
            reply_markup=reply_markup
        )
        return
    
    # Обновляем покупателя в сделке
    update_deal_buyer(deal_id, user_id)
    
    # Уведомляем продавца
    try:
        await context.bot.send_message(
            deal['seller_id'],
            f"👤 Пользователь @{user.username or user.first_name} присоединился к сделке\n"
            f"📌 #{deal_id}\n"
            f"• Успешные сделки: 0\n\n"
            f"⚠️ Проверьте, что это тот же пользователь, с которым вы вели диалог ранее!\n"
            f"❌ Не переводите подарок до получения подтверждения оплаты в этом чате!"
        )
    except Exception:
        pass
    
    # Показываем покупателю информацию для оплаты
    keyboard = [
        [InlineKeyboardButton("💎 Открыть в Tonkeeper", url=f"ton://transfer/{deal['payment_address']}?amount={int(deal['amount_ton']*1e9)}&text={deal_id}")],
        [InlineKeyboardButton("❌ Выйти из сделки", callback_data=f"leave_deal_{deal_id}")],
        [InlineKeyboardButton("🔙 Вернуться в меню", callback_data="back_to_main")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = (
        f"📌 *Информация о сделке #{deal_id}*\n\n"
        f"👤 Вы покупатель в сделке.\n"
        f"👨‍💼 Продавец: @{await get_username(deal['seller_id'], context)}\n"
        f"• Успешные сделки: 0\n\n"
        f"🛍 Вы покупаете: {deal['description']}\n\n"
        f"---\n\n"
        f"💳 *Адрес для оплаты:*\n`{deal['payment_address']}`\n\n"
        f"💰 *Сумма к оплате:*\n"
        f"• {deal['amount_px']} PX (+1% fee)\n"
        f"• {deal['amount_usdt']} USDT\n"
        f"• {deal['amount_ton']} TON\n\n"
        f"📝 *Комментарий к платежу (мемо):*\n`{deal['payment_memo']}`\n\n"
        f"⚠️ Пожалуйста, убедитесь в правильности данных перед оплатой. Комментарий обязателен!\n"
        f"После оплаты ожидайте автоматического подтверждения."
    )
    
    await update.message.reply_text(
        text,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )


async def get_username(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> str:
    """Получить username по ID"""
    try:
        chat = await context.bot.get_chat(user_id)
        return chat.username or str(user_id)
    except Exception:
        return str(user_id)


async def leave_deal(update: Update, context: ContextTypes.DEFAULT_TYPE, deal_id: str):
    """Покупатель выходит из сделки"""
    user_id = update.effective_user.id
    deal = get_deal(deal_id)
    
    if deal:
        update_deal_status(deal_id, "cancelled")
        
        # Уведомляем продавца
        try:
            await context.bot.send_message(
                deal['seller_id'],
                f"❌ Покупатель вышел из сделки #{deal_id}\nСделка отменена."
            )
        except Exception:
            pass
    
    keyboard = [[InlineKeyboardButton("🔙 Вернуться в меню", callback_data="back_to_main")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        "❌ Вы вышли из сделки.",
        reply_markup=reply_markup
    )


async def cancel_deal(update: Update, context: ContextTypes.DEFAULT_TYPE, deal_id: str):
    """Продавец отменяет сделку"""
    user_id = update.effective_user.id
    deal = get_deal(deal_id)
    
    if deal and deal['seller_id'] == user_id:
        update_deal_status(deal_id, "cancelled")
        
        # Уведомляем покупателя если есть
        if deal.get('buyer_id'):
            try:
                await context.bot.send_message(
                    deal['buyer_id'],
                    f"❌ Продавец отменил сделку #{deal_id}"
                )
            except Exception:
                pass
    
    keyboard = [[InlineKeyboardButton("🔙 Вернуться в меню", callback_data="back_to_main")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            "❌ Сделка отменена.",
            reply_markup=reply_markup
        )
