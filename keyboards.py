from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def main_menu(is_super_admin: bool = False, lang: str = 'ru') -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    from utils import t
    
    builder.row(
        InlineKeyboardButton(text=t('new_deal', lang), callback_data="new_deal", style="success"),
        InlineKeyboardButton(text=t('my_deals', lang), callback_data="my_deals")
    )
    builder.row(
        InlineKeyboardButton(text=t('profile', lang), callback_data="profile"),
        InlineKeyboardButton(text=t('requisites', lang), callback_data="requisites")
    )
    builder.row(
        InlineKeyboardButton(text=t('withdraw', lang), callback_data="withdraw"),
        InlineKeyboardButton(text=t('scam_base', lang), callback_data="scam_base")
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
        InlineKeyboardButton(text=t('channel', lang), url="https://t.me/playerok", style="primary"),
        InlineKeyboardButton(text=t('support', lang), url="https://t.me/playerok", style="primary")
    )
    
    # Кнопки смены языка
    builder.row(
        InlineKeyboardButton(text="🇷🇺 RU", callback_data="set_lang_ru", style="success" if lang == 'ru' else "default"),
        InlineKeyboardButton(text="🇺🇸 EN", callback_data="set_lang_en", style="success" if lang == 'en' else "default")
    )
    
    return builder.as_markup()

def deal_type_menu(lang: str = 'ru') -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    from utils import t
    builder.row(
        InlineKeyboardButton(text=t('gift', lang), callback_data="type_gift"),
        InlineKeyboardButton(text=t('account', lang), callback_data="type_account")
    )
    builder.row(
        InlineKeyboardButton(text=t('other', lang), callback_data="type_other")
    )
    builder.row(
        InlineKeyboardButton(text=t('back', lang), callback_data="menu")
    )
    return builder.as_markup()

def currency_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🇷🇺 RUB", callback_data="cur_RUB"),
        InlineKeyboardButton(text="🇰🇿 KZT", callback_data="cur_KZT"),
        InlineKeyboardButton(text="🇺🇦 UAH", callback_data="cur_UAH")
    )
    builder.row(
        InlineKeyboardButton(text="🇧🇾 BYN", callback_data="cur_BYN"),
        InlineKeyboardButton(text="🇪🇺 EUR", callback_data="cur_EUR"),
        InlineKeyboardButton(text="🇺🇸 USD", callback_data="cur_USD")
    )
    builder.row(
        InlineKeyboardButton(text="⭐ Stars", callback_data="cur_STARS")
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_deal_type")
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
