from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def main_menu(is_super_admin: bool = False) -> InlineKeyboardMarkup:
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
    
    if is_super_admin:
        builder.row(
            InlineKeyboardButton(text="➕ Добавить админа", callback_data="admin_add", style="success"),
            InlineKeyboardButton(text="➖ Удалить админа", callback_data="admin_remove", style="success")
        )
        builder.row(
            InlineKeyboardButton(text="📝 Рассылка", callback_data="admin_broadcast", style="success"),
            InlineKeyboardButton(text="👥 Список админов", callback_data="admin_list", style="success")
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
    return builder.as_markup()
