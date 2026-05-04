import os
import asyncio
import telebot
from telebot import types
from FunPayNexusAPI import Bot as FunPayBot, Dispatcher

# --- Инициализация ---
TOKEN = os.environ['TELEGRAM_BOT_TOKEN']
GOLDEN_KEY = os.environ['FUNPAY_GOLDEN_KEY']
ADMIN_ID = int(os.environ['TELEGRAM_CHAT_ID'])

bot = telebot.TeleBot(TOKEN)

# --- Инициализация FunPay клиента ---
funpay_bot = FunPayBot(golden_key=GOLDEN_KEY)
dispatcher = Dispatcher(funpay_bot)

async def get_funpay_profile():
    """Функция для получения информации о профиле FunPay."""
    try:
        account = dispatcher.account
        username = await account.username
        balance = await account.balance
        lots = await account.get_lots() # <-- Вот он, метод для получения лотов!
        return username, balance, lots
    except Exception as e:
        raise e

def get_profile_sync():
    """Обёртка для вызова асинхронной функции."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        username, balance, lots = loop.run_until_complete(get_funpay_profile())
        return username, balance, lots
    finally:
        loop.close()

# --- Кнопка "Активные предложения" ---
@bot.callback_query_handler(func=lambda call: call.data == "show_lots")
def callback_show_lots(call):
    try:
        username, balance, lots = get_profile_sync()
        if not lots:
            bot.send_message(call.message.chat.id, "🏷 У вас пока нет активных предложений.")
            return
        
        # Формируем сообщение со списком лотов
        text = f"👤 Продавец: **{username}**\n💰 Баланс: **{balance} руб.**\n\n📦 **Активные предложения ({len(lots)} шт.):**\n\n"
        for lot in lots:
            # Адаптируй поля под реальный объект lot (скорее всего, это словарь)
            lot_id = lot.get('id', 'Н/Д')
            lot_desc = lot.get('description', 'Без названия')
            lot_price = lot.get('price', 'Н/Д')
            text += f"• **{lot_desc}**\n  ID: `{lot_id}` | 💵 Цена: {lot_price} руб.\n\n"
            if len(text) > 3500: # Защита от превышения лимита Telegram
                text += "...\n(показаны не все лоты)"
                break

        bot.send_message(call.message.chat.id, text, parse_mode="Markdown")
    except Exception as e:
        bot.send_message(call.message.chat.id, f"❌ Ошибка при получении лотов: {e}")
    finally:
        bot.answer_callback_query(call.id)
