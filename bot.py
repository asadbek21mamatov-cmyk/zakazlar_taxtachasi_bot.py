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

# Mijozlarning buyurtma tarixini saqlash uchun lug'at
# Format: {chat_id: [{'type': 'Plombir', 'quantity': '2 ta', 'date': '2026-04-23 15:30'}, ...]}
user_orders = {}

# Bosh menyuni chiqaruvchi funksiya
def get_main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🛒 Yangi buyurtma", "📜 Zakaz tarixi")
    return markup

# /start buyrug'i
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(
        message.chat.id, 
        "🍦 Assalomu alaykum! Muzqaymoqlar botiga xush kelibsiz!\n\n"
        "Quyidagi menyudan kerakli bo'limni tanlang:", 
        reply_markup=get_main_menu()
    )

# Bosh menyu tugmalarini boshqarish
@bot.message_handler(func=lambda message: message.text in ["🛒 Yangi buyurtma", "📜 Zakaz tarixi"])
def handle_main_menu(message):
    if message.text == "🛒 Yangi buyurtma":
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add(types.KeyboardButton("📱 Telefon raqamni yuborish", request_contact=True))
        markup.add("❌ Bosh menyu")
        bot.send_message(
            message.chat.id, 
            "Buyurtma berish uchun pastdagi tugma orqali telefon raqamingizni yuboring:", 
            reply_markup=markup
        )
        bot.register_next_step_handler(message, process_phone)
        
    elif message.text == "📜 Zakaz tarixi":
        history = user_orders.get(message.chat.id, [])
        if not history:
            bot.send_message(
                message.chat.id, 
                "Sizda hali buyurtmalar tarixi yo'q 😔", 
                reply_markup=get_main_menu()
            )
        else:
            text = "<b>Sizning buyurtmalar tarixingiz:</b>\n\n"
            for i, order in enumerate(history, 1):
                text += f"{i}. <b>{order['type']}</b> - {order['quantity']} <i>({order['date']})</i>\n"
            
            bot.send_message(message.chat.id, text, parse_mode='HTML', reply_markup=get_main_menu())

# 1-qadam: Raqamni qabul qilish
def process_phone(message):
    try:
        if message.text == "❌ Bosh menyu":
            bot.send_message(message.chat.id, "Bosh menyuga qaytdik:", reply_markup=get_main_menu())
            return

        phone = message.contact.phone_number if message.contact else message.text
        clean_phone = re.sub(r'\D', '', phone)
        is_valid = False

        if len(clean_phone) == 9:
            clean_phone = '998' + clean_phone
            is_valid = True
        elif len(clean_phone) == 12 and clean_phone.startswith('998'):
            is_valid = True

        if is_valid:
            formatted_phone = f"+{clean_phone[:3]} {clean_phone[3:5]} {clean_phone[5:8]} {clean_phone[8:10]} {clean_phone[10:12]}"
            
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
            markup.add("🍫 Shokoladli", "🍓 Qulupnayli", "🍦 Vanilli", "🍋 Limonli", "🎂 Plombir", "❌ Bosh menyu")

            bot.send_message(
                message.chat.id, 
                f"✅ Raqamingiz qabul qilindi: {formatted_phone}\n\nQanday muzqaymoq xohlaysiz?",
                reply_markup=markup
            )
            bot.register_next_step_handler(message, process_ice_cream, formatted_phone)
        else:
            bot.send_message(message.chat.id, "❌ Noto'g'ri format! Qaytadan urinib ko'ring.")
            bot.register_next_step_handler(message, process_phone)
            
    except Exception as e:
        logging.error(f"Xatolik: {e}")
        bot.send_message(message.chat.id, "Xatolik yuz berdi. /start ni bosing.")

# 2-qadam: Muzqaymoq turini qabul qilish
def process_ice_cream(message, phone_number):
    try:
        ice_cream_type = message.text

        if ice_cream_type == "❌ Bosh menyu":
            bot.send_message(message.chat.id, "Bosh menyuga qaytdik:", reply_markup=get_main_menu())
            return

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
        markup.add("1 ta", "2 ta", "3 ta", "4 ta", "5 ta", "1 kg", "❌ Bosh menyu")

        bot.send_message(
            message.chat.id, 
            f"Siz <b>{ice_cream_type}</b> tanladingiz.\n\nEndi miqdorini tanlang:",
            reply_markup=markup,
            parse_mode='HTML'
        )
        bot.register_next_step_handler(message, process_quantity, phone_number, ice_cream_type)
            
    except Exception as e:
        bot.send_message(message.chat.id, "Xatolik yuz berdi. /start ni bosing.")

# 3-qadam: Miqdorni qabul qilish va saqlash
def process_quantity(message, phone_number, ice_cream_type):
    try:
        quantity = message.text
        
        if quantity == "❌ Bosh menyu":
            bot.send_message(message.chat.id, "Bosh menyuga qaytdik:", reply_markup=get_main_menu())
            return

        user_name = message.from_user.first_name
        username = f"@{message.from_user.username}" if message.from_user.username else "Mavjud emas"
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M") # Hozirgi vaqt

        # 1. TARIXGA SAQLASH (Eng muhim qism)
        if message.chat.id not in user_orders:
            user_orders[message.chat.id] = []
            
        user_orders[message.chat.id].append({
            "type": ice_cream_type,
            "quantity": quantity,
            "date": current_time
        })

        # 2. Mijozga tasdiq va Bosh menyuni qaytarish
        bot.send_message(
            message.chat.id, 
            f"🎉 Rahmat, {user_name}! Buyurtmangiz qabul qilindi.\n"
            f"🛵 Kuryerimiz tez orada siz bilan bog'lanadi.",
            reply_markup=get_main_menu() # Tugatgach, bosh menyuni yana chiqaramiz
        )
        
        # 3. Kanalga yuborish
        channel_text = (
            "🚨 <b>YANGI BUYURTMA!</b> 🍦\n\n"
            f"👤 <b>Mijoz:</b> {user_name} ({username})\n"
            f"📞 <b>Raqam:</b> {phone_number}\n"
            f"🍨 <b>Muzqaymoq:</b> {ice_cream_type}\n"
            f"⚖️ <b>Miqdori:</b> {quantity}\n"
            f"⏰ <b>Vaqti:</b> {current_time}"
        )
        bot.send_message(CHANNEL_USERNAME, channel_text, parse_mode='HTML')
            
    except Exception as e:
        logging.error(f"Xatolik: {e}")
        bot.send_message(message.chat.id, "Xatolik yuz berdi. /start ni bosing.")

if __name__ == '__main__':
    logging.info("Muzqaymoq boti ishga tushdi...")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
