import os
import telebot
from telebot import types
from funpay import FunPay  # библиотека funpay-api

# ---------- Инициализация ----------
TOKEN = os.environ['TELEGRAM_BOT_TOKEN']
GOLDEN_KEY = os.environ['FUNPAY_GOLDEN_KEY']
ADMIN_ID = int(os.environ['TELEGRAM_CHAT_ID'])

bot = telebot.TeleBot(TOKEN)

# ---------- Функция проверки подключения к FunPay ----------
def check_funpay_connection():
    try:
        fp = FunPay(GOLDEN_KEY)
        # Пробуем получить хотя бы количество лотов
        lots = fp.get_lots()
        return True, f"✅ Подключено! Найдено лотов: {len(lots)}"
    except Exception as e:
        return False, f"❌ Ошибка подключения: {e}"

# ---------- Команда /start (на всякий случай) ----------
@bot.message_handler(commands=['start'])
def start(message):
    show_main_menu(message.chat.id)

# ---------- Главное меню с кнопкой ----------
def show_main_menu(chat_id):
    connected, status_text = check_funpay_connection()
    markup = types.InlineKeyboardMarkup()
    if connected:
        markup.add(types.InlineKeyboardButton("📋 Активные предложения", callback_data="show_lots"))
    else:
        markup.add(types.InlineKeyboardButton("🔄 Проверить снова", callback_data="check_again"))
    bot.send_message(chat_id, status_text, reply_markup=markup)

# ---------- Обработчик нажатий на кнопки ----------
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if call.data == "show_lots":
        try:
            fp = FunPay(GOLDEN_KEY)
            lots = fp.get_lots()
            if not lots:
                bot.send_message(call.message.chat.id, "У вас нет активных предложений.")
            else:
                # Формируем список лотов (название, цена, id)
                text = "📦 **Ваши активные предложения:**\n"
                for lot in lots[:30]:  # ограничим вывод 30 штуками, чтобы не упереться в лимит Telegram
                    title = lot.title if hasattr(lot, 'title') else str(lot)
                    price = f"{lot.price} {lot.currency}" if hasattr(lot, 'price') else "???"
                    text += f"• `{lot.id}` — {title} — {price}\n"
                text += f"\nВсего: {len(lots)} шт."
                bot.send_message(call.message.chat.id, text, parse_mode="Markdown")
        except Exception as e:
            bot.send_message(call.message.chat.id, f"⚠️ Не удалось загрузить список: {e}")
    elif call.data == "check_again":
        show_main_menu(call.message.chat.id)
    bot.answer_callback_query(call.id)

# ---------- Запуск ----------
if __name__ == '__main__':
    # Сразу после старта отправляем меню администратору
    try:
        show_main_menu(ADMIN_ID)
    except Exception as e:
        print(f"Ошибка при стартовом сообщении: {e}")
    # Затем запускаем бесконечное прослушивание команд
    bot.infinity_polling()
