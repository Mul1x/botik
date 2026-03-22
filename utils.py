def format_amount(amount: float) -> str:
    return f"{amount:,.2f}".replace(",", " ")

def get_rating_stars(rating: float) -> str:
    return "★" * int(rating) + "☆" * (5 - int(rating))

MESSAGES = {
    'ru': {
        'main_menu': "<b>🛡️ GIFT GUARD</b>\n\nПривет, {name}!\n<b>Рейтинг:</b> {rating} ({val}/5) | <b>Сделок:</b> {deals}\n\nДобро пожаловать в гарант-сервис для безопасных сделок!\nGIFT GUARD — сервис, который предоставляет возможность <b>безопасно</b> продавать и покупать любые товары. Мы обеспечиваем <b>защиту обеих сторон</b>, прозрачные условия и <b>быстрые выплаты</b>.\n\n---\n\n<b>Статистика:</b>\n- Выплачено: {total} RUB\n- Комиссия сервиса: 1.5%\n\nНажмите кнопки ниже, чтобы начать!",
        'new_deal': "🟢 Новая сделка",
        'my_deals': "📋 Мои сделки",
        'profile': "👤 Профиль",
        'requisites': "💳 Реквизиты",
        'withdraw': "💰 Вывод",
        'scam_base': "⚠️ Скам база",
        'channel': "📢 Канал",
        'support': "🆘 Поддержка",
        'select_type': "Выберите тип сделки:",
        'gift': "🎁 Подарок",
        'account': "👤 Аккаунт",
        'other': "📦 Другое",
        'back': "◀️ Назад в меню",
        'select_currency': "<b>Выберите валюту для суммы {amount}:</b>",
        'deal_created': "✅ <b>Сделка успешно создана!</b>\n\n<b>Тип:</b> {type}\n<b>Товар:</b> {desc}\n<b>Сумма:</b> {amount} {cur}\n\n<b>ID сделки:</b> {id}\n\n---\n\n<b>Ссылка для покупателя:</b>\n<code>{link}</code>\n\n⚠️ <b>Передавайте товар только после получения уведомления об оплате!</b>",
        'lang_btn': "🇷🇺 Русский",
        'pay_btn': "✅ Оплатить",
        'cancel_btn': "❌ Отмена",
        'buyer_paid': "💰 <b>Покупатель оплатил сделку #{id}</b>\n\n📦 <b>Тип:</b> {type}\n📋 <b>Товар:</b> {desc}\n💵 <b>Сумма:</b> +{amount} {cur}\n\n👤 <b>Покупатель:</b> ID {buyer_id}\n\n<i>✅ Деньги поступили. Можете передавать товар/подарок.</i>\n\n🎁 <b>ИНСТРУКЦИЯ ПО ПЕРЕДАЧЕ ПОДАРКА</b>\n\n1. 📦 Передайте подарок гаранту: @garantmoskow\n2. ✅ Передача подтвержаеся автоматически\n3. 💰 После подтверждения средства будут зачислены на ваш баланс",
    },
    'en': {
        'main_menu': "<b>🛡️ GIFT GUARD</b>\n\nHello, {name}!\n<b>Rating:</b> {rating} ({val}/5) | <b>Deals:</b> {deals}\n\nWelcome to the escrow service for safe deals!\nGIFT GUARD is a service that provides the opportunity to <b>safely</b> sell and buy any goods. We provide <b>protection for both parties</b>, transparent conditions and <b>fast payouts</b>.\n\n---\n\n<b>Statistics:</b>\n- Paid out: {total} RUB\n- Service fee: 1.5%\n\nClick the buttons below to start!",
        'new_deal': "🟢 New Deal",
        'my_deals': "📋 My Deals",
        'profile': "👤 Profile",
        'requisites': "💳 Requisites",
        'withdraw': "💰 Withdraw",
        'scam_base': "⚠️ Scam Base",
        'channel': "📢 Channel",
        'support': "🆘 Support",
        'select_type': "Select deal type:",
        'gift': "🎁 Gift",
        'account': "👤 Account",
        'other': "📦 Other",
        'back': "◀️ Back to menu",
        'select_currency': "<b>Select currency for amount {amount}:</b>",
        'deal_created': "✅ <b>Deal created successfully!</b>\n\n<b>Type:</b> {type}\n<b>Item:</b> {desc}\n<b>Amount:</b> {amount} {cur}\n\n<b>Deal ID:</b> {id}\n\n---\n\n<b>Link for buyer:</b>\n<code>{link}</code>\n\n⚠️ <b>Transfer the item only after receiving payment notification!</b>",
        'lang_btn': "🇺🇸 English",
        'pay_btn': "✅ Pay",
        'cancel_btn': "❌ Cancel",
        'buyer_paid': "💰 <b>Buyer paid for deal #{id}</b>\n\n📦 <b>Type:</b> {type}\n📋 <b>Item:</b> {desc}\n💵 <b>Amount:</b> +{amount} {cur}\n\n👤 <b>Buyer:</b> ID {buyer_id}\n\n<i>✅ Money received. You can transfer the item/gift.</i>\n\n🎁 <b>GIFT TRANSFER INSTRUCTIONS</b>\n\n1. 📦 Transfer the gift to the guarantor: @garantmoskow\n2. ✅ Transfer is confirmed automatically\n3. 💰 After confirmation, funds will be credited to your balance",
    }
}

def t(key: str, lang: str = 'ru') -> str:
    return MESSAGES.get(lang, MESSAGES['ru']).get(key, key)
