from telegram import Update
from telegram.ext import ContextTypes

from handlers.menu import show_main_menu, support, referral, change_language
from handlers.wallet import manage_wallets, add_ton_wallet_start, add_sbp_start, add_rf_card_start, add_ua_card_start, add_stars
from handlers.deal import create_deal_start, cancel_deal, leave_deal
from handlers.admin import admin_panel, admin_add_start, admin_remove_start, admin_remove_confirm, confirm_payment
from database import is_admin, get_deal


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик всех callback-запросов"""
    query = update.callback_query
    data = query.data
    
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
    
    # Управление кошельками
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
    
    # Админ-панель
    elif data == "admin_add":
        await admin_add_start(update, context)
    
    elif data == "admin_remove":
        await admin_remove_start(update, context)
    
    elif data.startswith("admin_remove_"):
        user_id_to_remove = int(data.split("_")[2])
        await admin_remove_confirm(update, context, user_id_to_remove)
    
    # Работа со сделками
    elif data.startswith("cancel_deal_"):
        deal_id = data.split("_")[2]
        await cancel_deal(update, context, deal_id)
    
    elif data.startswith("leave_deal_"):
        deal_id = data.split("_")[2]
        await leave_deal(update, context, deal_id)
    
    elif data.startswith("confirm_payment_"):
        deal_id = data.split("_")[2]
        await confirm_payment(update, context, deal_id)
    
    elif data.startswith("copy_link_"):
        deal_id = data.split("_")[2]
        await query.answer(f"Ссылка скопирована: t.me/GiftsOkBot?start=deal_{deal_id}")
    
    # Языки (пока просто заглушка)
    elif data.startswith("lang_"):
        await query.answer("Язык временно недоступен")
    
    else:
        await query.answer("Неизвестная команда")
