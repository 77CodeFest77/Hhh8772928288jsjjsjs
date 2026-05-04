import os
import telebot
from telebot import types
from FunPayAPI import Account

# ---------- Инициализация ----------
TOKEN = os.environ['TELEGRAM_BOT_TOKEN']
GOLDEN_KEY = os.environ['FUNPAY_GOLDEN_KEY']
ADMIN_ID = int(os.environ['TELEGRAM_CHAT_ID'])

bot = telebot.TeleBot(TOKEN)
fp_account = Account(GOLDEN_KEY).get()  # основное подключение к FunPay

# ---------- Проверка подключения ----------
def check_connection():
    try:
        lots = fp_account.get_lots()
        return True, f"✅ Подключено! Найдено лотов: {len(lots)}"
    except Exception as e:
        return False, f"❌ Ошибка подключения: {e}"

# ---------- Стартовое меню ----------
def show_menu(chat_id):
    connected, status_text = check_connection()
    markup = types.InlineKeyboardMarkup()
    if connected:
        markup.add(types.InlineKeyboardButton("📋 Активные предложения", callback_data="show_lots"))
    else:
        markup.add(types.InlineKeyboardButton("🔄 Проверить снова", callback_data="check_again"))
    bot.send_message(chat_id, status_text, reply_markup=markup)

# ---------- Обработчик кнопок ----------
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if call.data == "show_lots":
        try:
            lots = fp_account.get_lots()
            if not lots:
                bot.send_message(call.message.chat.id, "У вас нет активных предложений.")
            else:
                text = "📦 **Активные предложения:**\n"
                for lot in lots[:30]:  # ограничение, чтобы не превысить лимит Telegram
                    lot_id = lot.id
                    title = getattr(lot, 'description', None) or getattr(lot, 'title', 'Без названия')
                    price = f"{lot.price} {lot.currency}" if hasattr(lot, 'price') else "???"
                    text += f"• `{lot_id}` — {title} — {price}\n"
                text += f"\nВсего: {len(lots)} шт."
                bot.send_message(call.message.chat.id, text, parse_mode="Markdown")
        except Exception as e:
            bot.send_message(call.message.chat.id, f"⚠️ Не удалось загрузить список: {e}")
    elif call.data == "check_again":
        show_menu(call.message.chat.id)
    bot.answer_callback_query(call.id)

# ---------- При запуске ----------
if __name__ == '__main__':
    try:
        show_menu(ADMIN_ID)  # отправляем статус администратору
    except Exception as e:
        print(f"Не удалось отправить стартовое сообщение: {e}")
    bot.infinity_polling()
