import os
import telebot
from telebot import types
import requests
from bs4 import BeautifulSoup

TELEGRAM_TOKEN = os.environ['TELEGRAM_BOT_TOKEN']
GOLDEN_KEY = os.environ['FUNPAY_GOLDEN_KEY']
ADMIN_ID = int(os.environ['TELEGRAM_CHAT_ID'])

bot = telebot.TeleBot(TELEGRAM_TOKEN)
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

    # Вариант 1: .offer-list-item с data-id (старый)
    for item in soup.select('.offer-list-item'):
        try:
            title_el = item.select_one('.offer-list-item-title')
            price_el = item.select_one('.tc-price')
            if title_el and price_el:
                title = title_el.get_text(strip=True)
                price = price_el.get_text(strip=True)
                lot_id = item.get('data-id', '')
                lots.append({'id': lot_id, 'title': title, 'price': price})
        except:
            continue

    # Вариант 2: Блоки с классом .tc-item (более новый дизайн)
    if not lots:
        for item in soup.select('.tc-item'):
            try:
                title_el = item.select_one('.tc-item-title, .tc-desc, .lot-title')
                price_el = item.select_one('.tc-price, .price, .lot-price')
                lot_id = item.get('data-id', item.get('id', ''))
                if title_el and price_el:
                    title = title_el.get_text(strip=True)
                    price = price_el.get_text(strip=True)
                    lots.append({'id': lot_id, 'title': title, 'price': price})
            except:
                continue

    # Вариант 3: Ищем любые строки таблицы с data-id
    if not lots:
        for row in soup.find_all('tr', attrs={'data-id': True}):
            try:
                cells = row.find_all('td')
                if len(cells) >= 3:
                    title = cells[0].get_text(strip=True)
                    price = cells[2].get_text(strip=True)
                    lot_id = row['data-id']
                    lots.append({'id': lot_id, 'title': title, 'price': price})
            except:
                continue

    # Диагностика: если лотов нет, отправляем фрагмент HTML
    if not lots:
        body = soup.find('body')
        if body:
            snippet = str(body)[:2000]
            bot.send_message(ADMIN_ID, f"⚠️ Лоты не найдены. HTML-фрагмент:\n\n{snippet}")
        else:
            bot.send_message(ADMIN_ID, "⚠️ Пустая страница с лотами. Возможно, требуется повторная авторизация.")
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
            bot.send_message(call.message.chat.id, "🏷 Нет активных предложений (или не удалось распознать).")
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
    conn, text = check_connection()
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📋 Активные предложения", callback_data="lots"))
    bot.send_message(ADMIN_ID, text, reply_markup=markup)
    bot.infinity_polling()
