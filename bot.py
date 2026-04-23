import os
import re
import logging
import telebot
from telebot import types
from datetime import datetime

# Loglarni sozlash
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

TOKEN = os.getenv('BOT_TOKEN', '8787588894:AAHo5YdG3H_klIcxmjtKcOj5I-Va0e6sZyI')
bot = telebot.TeleBot(TOKEN)
CHANNEL_USERNAME = '@zakaz_taxtachasi'

# Xotiralar
user_orders = {}
current_order = {}

# /menyu buyrug'i yozilganda ishlaydi
@bot.message_handler(commands=['menyu'])
def send_main_menu(message): # message qo'shildi
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🛒 Yangi buyurtma", "📜 Zakaz tarixi")
    
    # Tugmalarni matn bilan birga yuborish kerak
    bot.send_message(message.chat.id, "Bosh menyu:", reply_markup=markup)

# /start buyrug'i
@bot.message_handler(commands=['start'])
def send_welcome(message):
    if message.chat.id in current_order:
        del current_order[message.chat.id]
        
    bot.send_message(
        message.chat.id, 
        "🍦 Assalomu alaykum! Shirin muzqaymoqlar botiga xush kelibsiz!\n\n"
        "Quyidagi menyudan tanlang:", 
        reply_markup=get_main_menu()
    )

# Menyularni boshqarish
@bot.message_handler(func=lambda message: message.text in ["🛒 Yangi buyurtma", "📜 Zakaz tarixi", "❌ Bekor qilish"])
def handle_menu_clicks(message):
    if message.text in ["📜 Zakaz tarixi"]:
        history = user_orders.get(message.chat.id, [])
        if not history:
            bot.send_message(message.chat.id, "Sizda hali buyurtmalar tarixi yo'q 😔", reply_markup=get_main_menu())
        else:
            text = "<b>Sizning buyurtmalar tarixingiz:</b>\n\n"
            for i, order in enumerate(history, 1):
                text += f"{i}. <b>{order['type']}</b> - {order['qty']} {order['unit']} <i>({order['date']})</i>\n"
            bot.send_message(message.chat.id, text, parse_mode='HTML', reply_markup=get_main_menu())
            
    elif message.text in ["🛒 Yangi buyurtma", "❌ Bekor qilish"]:
        current_order[message.chat.id] = {}
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add(types.KeyboardButton("📱 Telefon raqamni yuborish", request_contact=True))
        markup.add("❌ Bosh menyu")
        bot.send_message(
            message.chat.id, 
            "Boshladik! Avval pastdagi tugma orqali telefon raqamingizni yuboring:", 
            reply_markup=markup
        )
        bot.register_next_step_handler(message, process_phone)

# 1. Raqamni qabul qilish
def process_phone(message):
    if message.text == "❌ Bosh menyu":
        send_welcome(message)
        return

    phone = message.contact.phone_number if message.contact else message.text
    clean_phone = re.sub(r'\D', '', phone) if phone else ""
    
    if len(clean_phone) >= 9:
        if len(clean_phone) == 9: clean_phone = '998' + clean_phone
        formatted_phone = f"+{clean_phone[:3]} {clean_phone[3:5]} {clean_phone[5:8]} {clean_phone[8:10]} {clean_phone[10:12]}"
        
        current_order[message.chat.id]['phone'] = formatted_phone
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add("🍫 Shokoladli", "🍓 Qulupnayli", "🍦 Vanilli", "🍋 Limonli", "🎂 Plombir", "❌ Bekor qilish")

        bot.send_message(message.chat.id, "✅ Raqam qabul qilindi.\n\n🍨 Qanday muzqaymoq xohlaysiz?", reply_markup=markup)
        bot.register_next_step_handler(message, process_ice_cream)
    else:
        bot.send_message(message.chat.id, "❌ Noto'g'ri raqam. Qaytadan kiriting:")
        bot.register_next_step_handler(message, process_phone)

# 2. Muzqaymoq turini qabul qilish
def process_ice_cream(message):
    if message.text == "❌ Bekor qilish":
        send_welcome(message)
        return

    current_order[message.chat.id]['type'] = message.text
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("📦 Dona", "⚖️ Kilogramm (kg)", "❌ Bekor qilish")
    
    bot.send_message(
        message.chat.id, 
        f"Siz <b>{message.text}</b> tanladingiz.\n\nQanday o'lchovda xohlaysiz?", 
        reply_markup=markup, parse_mode='HTML'
    )
    bot.register_next_step_handler(message, process_unit)

# 3. O'lchov birligini qabul qilish va MIQDORNI QO'LDA yozishni so'rash
def process_unit(message):
    if message.text == "❌ Bekor qilish":
        send_welcome(message)
        return

    unit = "Dona" if "Dona" in message.text else "kg"
    current_order[message.chat.id]['unit'] = unit

    # Miqdor uchun faqat "Bekor qilish" tugmasini qoldiramiz, raqamni o'zi yozishi kerak
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    markup.add("❌ Bekor qilish")

    if unit == "Dona":
        bot.send_message(message.chat.id, "Necha dona xohlaysiz? (Raqamni yozib yuboring, masalan: 10):", reply_markup=markup)
    else:
        bot.send_message(message.chat.id, "Necha kilogramm xohlaysiz? (Raqamni yozib yuboring, masalan: 1.5):", reply_markup=markup)
        
    bot.register_next_step_handler(message, process_quantity)

# 4. Miqdorni qabul qilish va LOKATSIYANI so'rash
def process_quantity(message):
    if message.text == "❌ Bekor qilish":
        send_welcome(message)
        return

    current_order[message.chat.id]['qty'] = message.text

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    location_btn = types.KeyboardButton("📍 Joylashuvni yuborish (Avtomat)", request_location=True)
    markup.add(location_btn, "❌ Bekor qilish")

    bot.send_message(
        message.chat.id, 
        "Kuryerimiz yetkazib berishi uchun manzilingiz kerak.\n\n"
        "Pastdagi '📍 Joylashuvni yuborish' tugmasini bosing (shunda avtomat keladi) yoki manzilingizni matn qilib yozib yuboring:", 
        reply_markup=markup
    )
    bot.register_next_step_handler(message, process_location)

# 5. Lokatsiyani qabul qilish va KANALGA yuborish
def process_location(message):
    try:
        if message.text == "❌ Bekor qilish":
            send_welcome(message)
            return

        if message.location:
            latitude = message.location.latitude
            longitude = message.location.longitude
            map_link = f"https://maps.google.com/?q={latitude},{longitude}"
            location_text = f"<a href='{map_link}'>📍 Xaritada ko'rish</a>"
        else:
            location_text = message.text

        order_data = current_order.get(message.chat.id)
        if not order_data:
            send_welcome(message)
            return

        user_name = message.from_user.first_name
        username = f"@{message.from_user.username}" if message.from_user.username else "Mavjud emas"
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M")

        if message.chat.id not in user_orders:
            user_orders[message.chat.id] = []
        user_orders[message.chat.id].append({
            "type": order_data['type'],
            "qty": order_data['qty'],
            "unit": order_data['unit'],
            "date": current_time
        })

        bot.send_message(
            message.chat.id, 
            f"🎉 Rahmat, {user_name}! Buyurtmangiz qabul qilindi.\n"
            f"Kuryer tez orada yetib boradi.",
            reply_markup=get_main_menu()
        )

        channel_text = (
            "🚨 <b>YANGI BUYURTMA!</b> 🍦\n\n"
            f"👤 <b>Mijoz:</b> {user_name} ({username})\n"
            f"📞 <b>Raqam:</b> {order_data['phone']}\n"
            f"🍨 <b>Muzqaymoq:</b> {order_data['type']}\n"
            f"⚖️ <b>Miqdori:</b> {order_data['qty']} ({order_data['unit']})\n"
            f"⏰ <b>Vaqti:</b> {current_time}\n"
            f"🏠 <b>Manzil:</b> {location_text}"
        )
        bot.send_message(CHANNEL_USERNAME, channel_text, parse_mode='HTML', disable_web_page_preview=True)

        if message.location:
            bot.send_location(CHANNEL_USERNAME, latitude, longitude)

        del current_order[message.chat.id]

    except Exception as e:
        logging.error(f"Xatolik: {e}")
        bot.send_message(message.chat.id, "Kechirasiz, xatolik yuz berdi. /start ni bosing.")

if __name__ == '__main__':
    logging.info("Muzqaymoq boti ishga tushdi...")
    bot.infinity_polling(timeout=10, long_polling_timeout=5, skip_pending=True)
