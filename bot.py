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
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
})

def check_connection():
    try:
        r = session.get('https://funpay.com/orders/trade', timeout=10)
        return (True, "✅ Подключено к FunPay") if r.status_code == 200 else (False, "❌ Ошибка авторизации")
    except Exception as e:
        return False, f"❌ Сетевая ошибка: {e}"

def get_lots():
    # Основная страница с предложениями (иногда обновлённый дизайн)
    urls_to_try = [
        'https://funpay.com/lots/offer',
        'https://funpay.com/account/lots'   # резервная страница управления лотами
    ]
    lots = []
    used_html = ""

    for url in urls_to_try:
        try:
            r = session.get(url, timeout=15)
            soup = BeautifulSoup(r.text, 'html.parser')

            # Ищем любыми известными способами
            # 1) Старые классы
            for item in soup.select('.offer-list-item'):
                title_el = item.select_one('.offer-list-item-title')
                price_el = item.select_one('.tc-price')
                if title_el and price_el:
                    lots.append({
                        'id': item.get('data-id', ''),
                        'title': title_el.get_text(strip=True),
                        'price': price_el.get_text(strip=True)
                    })

            # 2) Новые классы (tc-item)
            if not lots:
                for item in soup.select('.tc-item'):
                    title_el = item.select_one('.tc-item-title, .tc-desc, .lot-title')
                    price_el = item.select_one('.tc-price, .price, .lot-price')
                    if title_el and price_el:
                        lots.append({
                            'id': item.get('data-id', item.get('id', '')),
                            'title': title_el.get_text(strip=True),
                            'price': price_el.get_text(strip=True)
                        })

            # 3) Таблица на странице account/lots
            if not lots:
                table = soup.select_one('table.table, table.lots-table, table.table-striped')
                if table:
                    for row in table.select('tbody tr'):
                        cells = row.find_all('td')
                        if len(cells) >= 3:
                            title = cells[0].get_text(strip=True)
                            price = cells[2].get_text(strip=True)
                            lot_id = row.get('data-id', '')
                            lots.append({'id': lot_id, 'title': title, 'price': price})

            if lots:
                break  # нашли, выходим из цикла

            used_html = str(soup.body)[:3500] if soup.body else "Пустое тело"

        except Exception as e:
            continue

    # Диагностика, если лотов нет
    if not lots:
        # Пробуем получить JSON через API (предположительный эндпоинт)
        try:
            r = session.get('https://funpay.com/lots/offer?action=filter', timeout=10)
            if r.status_code == 200 and r.headers.get('content-type', '').startswith('application/json'):
                data = r.json()
                if 'lots' in data:
                    for lot in data['lots']:
                        title = lot.get('description', '')
                        price = lot.get('price', '')
                        lot_id = lot.get('id', '')
                        lots.append({'id': lot_id, 'title': title, 'price': price})
        except:
            pass

    # Если всё равно пусто — отправляем фрагмент HTML для анализа
    if not lots:
        diagnostic_msg = "⚠️ Лоты не найдены. HTML-фрагмент:\n\n" + used_html[:3500]
        bot.send_message(ADMIN_ID, diagnostic_msg)

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
            bot.send_message(call.message.chat.id, "🏷 Нет активных предложений (или не удалось распознать). Если HTML был отправлен, перешли его мне.")
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
