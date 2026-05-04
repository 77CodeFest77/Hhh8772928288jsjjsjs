import os
import telebot
from telebot import types
import requests
from bs4 import BeautifulSoup

TELEGRAM_TOKEN = os.environ['TELEGRAM_BOT_TOKEN']
GOLDEN_KEY = os.environ['FUNPAY_GOLDEN_KEY']
ADMIN_ID = int(os.environ['TELEGRAM_CHAT_ID'])

bot = telebot.TeleBot(TELEGRAM_TOKEN)

# Сессия с авторизацией под FunPay
session = requests.Session()
session.cookies.set('golden_key', GOLDEN_KEY, domain='funpay.com')

def check_connection():
    try:
        r = session.get('https://funpay.com/orders/trade', timeout=10)
        if r.status_code == 200:
            return True, "✅ Подключено к FunPay"
        else:
            return False, "❌ Ошибка авторизации"
    except Exception as e:
        return False, f"❌ Сетевая ошибка: {e}"

def get_lots():
    r = session.get('https://funpay.com/lots/offer', timeout=15)
    soup = BeautifulSoup(r.text, 'html.parser')
    lots = []
    for item in soup.select('.offer-list-item'):
        try:
            title = item.select_one('.offer-list-item-title').get_text(strip=True)
            price = item.select_one('.tc-price').get_text(strip=True)
            lot_id = item.get('data-id', '')
            lots.append({'id': lot_id, 'title': title, 'price': price})
        except:
            continue
    return lots

@bot.message_handler(commands=['start'])
def start(message):
    conn, text = check_connection()
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📋 Активные предложения", callback_data="lots"))
    bot.send_message(message.chat.id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data == 'lots')
def show_lots(call):
    try:
        lots = get_lots()
        if not lots:
            bot.send_message(call.message.chat.id, "🏷 Нет активных предложений.")
            return
        text = "📦 **Твои лоты:**\n"
        for lot in lots[:30]:
            text += f"• {lot['title']} — {lot['price']} (ID: `{lot['id']}`)\n"
        text += f"\nВсего: {len(lots)} шт."
        bot.send_message(call.message.chat.id, text, parse_mode="Markdown")
    except Exception as e:
        bot.send_message(call.message.chat.id, f"⚠️ Ошибка: {e}")
    bot.answer_callback_query(call.id)

if __name__ == '__main__':
    # При запуске сразу уведомляем админа
    conn, text = check_connection()
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📋 Активные предложения", callback_data="lots"))
    bot.send_message(ADMIN_ID, text, reply_markup=markup)
    # И ЗАПУСКАЕМ БЕСКОНЕЧНОЕ ОЖИДАНИЕ КОМАНД
    bot.infinity_polling()
