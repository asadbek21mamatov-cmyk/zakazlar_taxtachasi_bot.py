import os
import re
import logging
import telebot
from telebot import types

# Loglarni sozlash
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Tokenni muhit o'zgaruvchisidan olamiz
TOKEN = os.getenv('BOT_TOKEN', '8787588894:AAHo5YdG3H_klIcxmjtKcOj5I-Va0e6sZyI')
bot = telebot.TeleBot(TOKEN)

# Buyurtmalar tushadigan kanal (silka emas, @ bilan boshlanadigan username yoziladi)
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
            
            # Muzqaymoqlar menyusini yaratamiz
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
            markup.add(
                "🍫 Shokoladli", "🍓 Qulupnayli", 
                "🍦 Vanilli", "🍋 Limonli", 
                "🎂 Plombir", "❌ Bekor qilish"
            )

            bot.send_message(
                message.chat.id, 
                f"✅ Raqamingiz qabul qilindi: {formatted_phone}\n\n"
                "🍨 Qanday muzqaymoq xohlaysiz? Pastdagi menyudan tanlang yoki o'zingiz yozib yuboring:",
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
        order_text = message.text
        user_name = message.from_user.first_name
        # Foydalanuvchining tg userneymi bo'lsa uni ham olamiz
        username = f"@{message.from_user.username}" if message.from_user.username else "Mavjud emas"

        # Bekor qilish tugmasi bosilsa
        if order_text == "❌ Bekor qilish":
            bot.send_message(
                message.chat.id, 
                "Buyurtma bekor qilindi. Qayta boshlash uchun /start buyrug'ini bosing.", 
                reply_markup=types.ReplyKeyboardRemove()
            )
            return

        # 1. Foydalanuvchiga chiroyli tasdiq xabari yuboramiz
        bot.send_message(
            message.chat.id, 
            f"🎉 Rahmat, {user_name}! Buyurtmangiz muvaffaqiyatli qabul qilindi.\n\n"
            f"🛒 Siz tanladingiz: <b>{order_text}</b>\n"
            "🛵 Kuryerimiz tez orada siz bilan bog'lanadi.",
            reply_markup=types.ReplyKeyboardRemove(),
            parse_mode='HTML'
        )
        
        # 2. Kanalga yuboriladigan xabar shabloni
        channel_text = (
            "🚨 <b>YANGI MUZQAYMOQ BUYURTMASI!</b> 🍦\n\n"
            f"👤 <b>Mijoz:</b> {user_name} ({username})\n"
            f"📞 <b>Raqam:</b> {phone_number}\n"
            f"🍨 <b>Buyurtma:</b> {order_text}"
        )
        
        # 3. Ma'lumotni @zakaz_taxtachasi kanaliga tashlash
        bot.send_message(CHANNEL_USERNAME, channel_text, parse_mode='HTML')
            
    except Exception as e:
        logging.error(f"Buyurtmani qabul qilishda xatolik: {e}")
        bot.send_message(
            message.chat.id, 
            "Kechirasiz, buyurtmani kanalga yuborishda xatolik yuz berdi. Bot kanalga admin ekanligini tekshiring."
        )

if __name__ == '__main__':
    logging.info("Muzqaymoq boti ishga tushdi...")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
