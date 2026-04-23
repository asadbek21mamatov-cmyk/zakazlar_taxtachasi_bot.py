import os
import re
import logging
import telebot
from telebot import types

# Loglarni sozlash
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

TOKEN = os.getenv('BOT_TOKEN', '8787588894:AAHo5YdG3H_klIcxmjtKcOj5I-Va0e6sZyI')
bot = telebot.TeleBot(TOKEN)
CHANNEL_USERNAME = '@zakaz_taxtachasi'

@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    contact_button = types.KeyboardButton("📱 Telefon raqamni yuborish", request_contact=True)
    markup.add(contact_button)
    
    bot.send_message(
        message.chat.id, 
        "🍦 Assalomu alaykum! Shirin va muzdek muzqaymoqlar botiga xush kelibsiz!\n\n"
        "Buyurtma berish uchun pastdagi tugma orqali telefon raqamingizni yuboring:", 
        reply_markup=markup
    )

@bot.message_handler(content_types=['contact', 'text'])
def handle_phone(message):
    try:
        if message.contact:
            phone = message.contact.phone_number
        else:
            phone = message.text

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
            markup.add(
                "🍫 Shokoladli", "🍓 Qulupnayli", 
                "🍦 Vanilli", "🍋 Limonli", 
                "🎂 Plombir", "❌ Bekor qilish"
            )

            bot.send_message(
                message.chat.id, 
                f"✅ Raqamingiz qabul qilindi: {formatted_phone}\n\n"
                "🍨 Qanday muzqaymoq xohlaysiz? Pastdagi menyudan tanlang:",
                reply_markup=markup
            )
            bot.register_next_step_handler(message, process_ice_cream_order, formatted_phone)
        else:
            bot.send_message(
                message.chat.id, 
                "❌ Noto'g'ri format! Iltimos, raqamni to'g'ri kiriting (Masalan: +998901234567)."
            )
            
    except Exception as e:
        logging.error(f"Xatolik: {e}")
        bot.send_message(message.chat.id, "Kechirasiz, xatolik yuz berdi. Qaytadan /start ni bosing.")

def process_ice_cream_order(message, phone_number):
    try:
        ice_cream_type = message.text

        if ice_cream_type == "❌ Bekor qilish":
            bot.send_message(
                message.chat.id, 
                "Buyurtma bekor qilindi. Qayta boshlash uchun /start buyrug'ini bosing.", 
                reply_markup=types.ReplyKeyboardRemove()
            )
            return

        # Yangi qadam: Miqdorni so'rash uchun tugmalar
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
        markup.add("1 ta", "2 ta", "3 ta", "4 ta", "5 ta", "1 kg", "❌ Bekor qilish")

        bot.send_message(
            message.chat.id, 
            f"Siz <b>{ice_cream_type}</b> tanladingiz.\n\n"
            "⚖️ Endi miqdorini tanlang yoki o'zingiz yozib yuboring (Masalan: 1.5 kg yoki 10 ta):",
            reply_markup=markup,
            parse_mode='HTML'
        )
        
        # Telefon raqam bilan birga muzqaymoq turini ham keyingi qadamga o'tkazamiz
        bot.register_next_step_handler(message, process_quantity, phone_number, ice_cream_type)
            
    except Exception as e:
        logging.error(f"Muzqaymoq turini qabul qilishda xatolik: {e}")
        bot.send_message(message.chat.id, "Kechirasiz, xatolik yuz berdi.")

# Yangi qadam: Miqdorni qabul qilish va kanalga yuborish
def process_quantity(message, phone_number, ice_cream_type):
    try:
        quantity = message.text
        user_name = message.from_user.first_name
        username = f"@{message.from_user.username}" if message.from_user.username else "Mavjud emas"

        if quantity == "❌ Bekor qilish":
            bot.send_message(
                message.chat.id, 
                "Buyurtma bekor qilindi. Qayta boshlash uchun /start buyrug'ini bosing.", 
                reply_markup=types.ReplyKeyboardRemove()
            )
            return

        # Foydalanuvchiga tasdiq xabari
        bot.send_message(
            message.chat.id, 
            f"🎉 Rahmat, {user_name}! Buyurtmangiz muvaffaqiyatli qabul qilindi.\n\n"
            f"🛒 Muzqaymoq turi: <b>{ice_cream_type}</b>\n"
            f"⚖️ Miqdori: <b>{quantity}</b>\n\n"
            "🛵 Kuryerimiz tez orada siz bilan bog'lanadi.",
            reply_markup=types.ReplyKeyboardRemove(),
            parse_mode='HTML'
        )
        
        # Kanalga yuboriladigan xabar shabloni
        channel_text = (
            "🚨 <b>YANGI MUZQAYMOQ BUYURTMASI!</b> 🍦\n\n"
            f"👤 <b>Mijoz:</b> {user_name} ({username})\n"
            f"📞 <b>Raqam:</b> {phone_number}\n"
            f"🍨 <b>Muzqaymoq turi:</b> {ice_cream_type}\n"
            f"⚖️ <b>Miqdori:</b> {quantity}"
        )
        
        bot.send_message(CHANNEL_USERNAME, channel_text, parse_mode='HTML')
            
    except Exception as e:
        logging.error(f"Miqdorni qabul qilishda xatolik: {e}")
        bot.send_message(
            message.chat.id, 
            "Kechirasiz, buyurtmani kanalga yuborishda xatolik yuz berdi."
        )

if __name__ == '__main__':
    logging.info("Muzqaymoq boti ishga tushdi...")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
