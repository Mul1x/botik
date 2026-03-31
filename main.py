import logging
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, 
    MessageHandler, ConversationHandler, filters
)
from config import TOKEN

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Инициализация базы данных
from database import init_db
init_db()

# Импорт обработчиков
from handlers.start import start
from handlers.menu import back_to_main, show_main_menu
from handlers.wallet import (
    add_ton_wallet_start, add_ton_wallet_receive,
    add_sbp_start, add_sbp_receive,
    add_rf_card_start, add_rf_card_receive,
    add_ua_card_start, add_ua_card_receive,
    add_stars
)
from handlers.deal import (
    create_deal_start, create_deal_amount, create_deal_description,
    join_deal, leave_deal, cancel_deal
)
from handlers.admin import admin_panel, admin_add_start, admin_add_receive, admin_remove_start
from handlers.callbacks import handle_callback
from config import (
    WAITING_DEAL_AMOUNT, WAITING_DEAL_DESCRIPTION,
    WAITING_TON_WALLET, WAITING_SBP_PHONE,
    WAITING_RF_CARD, WAITING_UA_CARD,
    WAITING_ADMIN_USERNAME
)


def main():
    application = Application.builder().token(TOKEN).build()

    # Обработчики команд
    application.add_handler(CommandHandler("start", start))
    
    # Обработчик колбэков
    application.add_handler(CallbackQueryHandler(handle_callback))
    
    # Обработчик присоединения к сделке через /start с параметром
    async def start_with_deal(update, context):
        if context.args and context.args[0].startswith("deal_"):
            deal_id = context.args[0].split("_")[1]
            await join_deal(update, context, deal_id)
        elif context.args and context.args[0].startswith("ref_"):
            # Обработка реферальной ссылки
            await start(update, context)
        else:
            await start(update, context)
    
    application.add_handler(CommandHandler("start", start_with_deal))
    
    # ConversationHandler для создания сделки
    create_deal_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(create_deal_start, pattern="^create_deal$")],
        states={
            WAITING_DEAL_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, create_deal_amount)],
            WAITING_DEAL_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, create_deal_description)],
        },
        fallbacks=[CallbackQueryHandler(back_to_main, pattern="^back_to_main$")],
    )
    application.add_handler(create_deal_conv)
    
    # ConversationHandler для добавления TON кошелька
    add_ton_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_ton_wallet_start, pattern="^add_ton_wallet$")],
        states={
            WAITING_TON_WALLET: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_ton_wallet_receive)],
        },
        fallbacks=[CallbackQueryHandler(back_to_main, pattern="^manage_wallets$")],
    )
    application.add_handler(add_ton_conv)
    
    # ConversationHandler для добавления СБП
    add_sbp_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_sbp_start, pattern="^add_sbp$")],
        states={
            WAITING_SBP_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_sbp_receive)],
        },
        fallbacks=[CallbackQueryHandler(back_to_main, pattern="^manage_wallets$")],
    )
    application.add_handler(add_sbp_conv)
    
    # ConversationHandler для добавления карты РФ
    add_rf_card_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_rf_card_start, pattern="^add_rf_card$")],
        states={
            WAITING_RF_CARD: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_rf_card_receive)],
        },
        fallbacks=[CallbackQueryHandler(back_to_main, pattern="^manage_wallets$")],
    )
    application.add_handler(add_rf_card_conv)
    
    # ConversationHandler для добавления карты UA
    add_ua_card_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_ua_card_start, pattern="^add_ua_card$")],
        states={
            WAITING_UA_CARD: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_ua_card_receive)],
        },
        fallbacks=[CallbackQueryHandler(back_to_main, pattern="^manage_wallets$")],
    )
    application.add_handler(add_ua_card_conv)
    
    # ConversationHandler для добавления админа
    add_admin_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_add_start, pattern="^admin_add$")],
        states={
            WAITING_ADMIN_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_receive)],
        },
        fallbacks=[CallbackQueryHandler(admin_panel, pattern="^admin_panel$")],
    )
    application.add_handler(add_admin_conv)
    
    # Запуск бота
    application.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()
