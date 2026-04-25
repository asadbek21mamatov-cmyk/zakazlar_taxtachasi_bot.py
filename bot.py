import os
import re
import logging
import telebot
from telebot import types
from datetime import datetime, timedelta
import pytz

# Loglarni sozlash
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

TOKEN = os.getenv('BOT_TOKEN', '8787588894:AAHo5YdG3H_klIcxmjtKcOj5I-Va0e6sZyI')
bot = telebot.TeleBot(TOKEN)
CHANNEL_USERNAME = '@zakaz_taxtachasi'

TASHKENT_TZ = pytz.timezone('Asia/Tashkent')

user_orders = {}
current_order = {}
user_status = {}

def get_uzbekistan_time():
    return datetime.now(TASHKENT_TZ)

def check_ban(chat_id):
    if chat_id in user_status and user_status[chat_id]['ban_until']:
        if get_uzbekistan_time() < user_status[chat_id]['ban_until']:
            return True 
        else:
            user_status[chat_id]['cancels'] = 0
            user_status[chat_id]['ban_until'] = None
            return False
    return False

def add_cancel(chat_id):
    if chat_id not in user_status:
        user_status[chat_id] = {'cancels': 0, 'ban_until': None}
    user_status[chat_id]['cancels'] += 1
    if user_status[chat_id]['cancels'] >= 3:
        user_status[chat_id]['ban_until'] = get_uzbekistan_time() + timedelta(hours=1)
        return True 
    return False

def get_main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🛒 Yangi buyurtma", "📜 Zakaz tarixi")
    return markup

@bot.message_handler(func=lambda message: check_ban(message.chat.id))
def handle_banned_users(message):
    ban_time = user_status[message.chat.id]['ban_until']
    left = ban_time - get_uzbekistan_time()
    minutes = int(left.total_seconds() / 60)
    bot.send_message(
        message.chat.id, 
        f"🚫 <b>Siz bloklangansiz!</b>\n\n1 soatga bloklandingiz.\n⏳ Qolgan vaqt: taxminan {minutes} daqiqa.",
        parse_mode='HTML'
    )

@bot.message_handler(commands=['start'])
def send_welcome(message):
    if check_ban(message.chat.id):
        handle_banned_users(message)
        return
    if message.chat.id in current_order:
        del current_order[message.chat.id]
    bot.send_message(
        message.chat.id, 
        "🍦 Assalomu alaykum! Shirin muzqaymoqlar botiga xush kelibsiz!\nQuyidagi menyudan tanlang:", 
        reply_markup=get_main_menu()
    )

def cancel_order(message):
    if add_cancel(message.chat.id):
        handle_banned_users(message)
    else:
        cancels = user_status[message.chat.id]['cancels']
        bot.send_message(
            message.chat.id, 
            f"Buyurtma bekor qilindi.\n⚠️ <i>Ogohlantirish: Siz {cancels}/3 marta bekor qildingiz.</i>", 
            reply_markup=get_main_menu(), parse_mode='HTML'
        )

@bot.message_handler(func=lambda message: message.text in ["🛒 Yangi buyurtma", "📜 Zakaz tarixi", "❌ Bekor qilish"])
def handle_menu_clicks(message):
    if check_ban(message.chat.id):
        return handle_banned_users(message)

    if message.text == "📜 Zakaz tarixi":
        history = user_orders.get(message.chat.id, [])
        if not history:
            bot.send_message(message.chat.id, "Sizda hali buyurtmalar tarixi yo'q", reply_markup=get_main_menu())
        else:
            text = "<b>Sizning tarixingiz:</b>\n\n"
            for i, order in enumerate(history, 1):
                receiver = order.get('receiver', 'Noma\'lum')
                text += f"{i}. <b>{order['type']}</b> - {order['qty']} {order['unit']} <i>({order['date']})</i> [Kimgaga: {receiver}]\n"
            bot.send_message(message.chat.id, text, parse_mode='HTML', reply_markup=get_main_menu())
            
    elif message.text == "❌ Bekor qilish":
        cancel_order(message)
        
    elif message.text == "🛒 Yangi buyurtma":
        current_order[message.chat.id] = {'allow_manual': False}
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
        markup.add("❌ Bekor qilish")
        bot.send_message(
            message.chat.id, 
            "Boshladik! Iltimos, muzqaymoqni qabul qilib oluvchining <b>Ism va Familiyasini</b> yozib yuboring:", 
            reply_markup=markup, parse_mode='HTML'
        )
        bot.register_next_step_handler(message, process_name)

def is_realistic_name(word):
    word_lower = word.lower()
    has_vowel = any(v in word_lower for v in "aeiouy")
    if not has_vowel:
        return False
    if re.search(r'(.)\1\1', word_lower):
        return False
    if re.search(r'[^aeiouy`\' ]{5,}', word_lower):
        return False
    return True

def process_name(message):
    if message.text == "❌ Bekor qilish": return cancel_order(message)
    
    name_text = re.sub(r'\s+', ' ', message.text.strip())
    words = name_text.split()
    
    is_valid = True
    if len(words) != 2:
        is_valid = False
    else:
        for word in words:
            alpha_word = word.replace("'", "").replace("`", "").replace("‘", "").replace("’", "")
            if not alpha_word.isalpha() or len(alpha_word) < 3:
                is_valid = False
            elif not is_realistic_name(alpha_word):
                is_valid = False
                
    if not is_valid:
        bot.send_message(
            message.chat.id, 
            "❌ Kiritilgan ism haqiqiyga o'xshamayapti!\n\n"
            "Iltimos, <b>faqat haqiqiy Ism va Familiya</b> kiriting (aniq 2 ta so'z).\n"
            "⚠️ Tushunarsiz yozuvlar (masalan: <i>asdfg</i>) qabul qilinmaydi.\n"
            "(Namuna: <i>Alisher Usmonov</i>):",
            parse_mode='HTML'
        )
        bot.register_next_step_handler(message, process_name)
        return
        
    formatted_name = f"{words[0].capitalize()} {words[1].capitalize()}"
    current_order[message.chat.id]['receiver'] = formatted_name
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(types.KeyboardButton("📱 Telefon raqamni yuborish", request_contact=True))
    markup.add("❌ Bekor qilish")
    bot.send_message(
        message.chat.id, 
        f"Yaxshi! Endi <b>{formatted_name}</b>ning telefon raqamini pastdagi tugma orqali yuboring:", 
        reply_markup=markup, parse_mode='HTML'
    )
    bot.register_next_step_handler(message, process_phone)

def process_phone(message):
    if message.text == "❌ Bekor qilish": return cancel_order(message)
    
    if message.contact:
        phone = message.contact.phone_number
        clean_phone = re.sub(r'\D', '', phone)
        
        if clean_phone.startswith('998') and len(clean_phone) == 12:
            formatted_phone = f"+{clean_phone[:3]} {clean_phone[3:5]} {clean_phone[5:8]} {clean_phone[8:10]} {clean_phone[10:12]}"
            current_order[message.chat.id]['phone'] = formatted_phone
            
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
            markup.add("🍫 Shokoladli", "🍓 Qulupnayli", "🍦 Vanilli", "🍋 Limonli", "🎂 Plombir", "❌ Bekor qilish")
            bot.send_message(message.chat.id, "✅ Raqam qabul qilindi.\n🍨 Qanday muzqaymoq xohlaysiz?", reply_markup=markup)
            bot.register_next_step_handler(message, process_ice_cream)
            return
        else:
            current_order[message.chat.id]['allow_manual'] = True
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
            markup.add("❌ Bekor qilish")
            bot.send_message(
                message.chat.id, 
                "⚠️ Sizning Telegram raqamingiz chet elga tegishli ekan.\n"
                "Iltimos, O'zbekiston telefon raqamingizni qo'lda yozib yuboring (Masalan: 901234567):",
                reply_markup=markup
            )
            bot.register_next_step_handler(message, process_phone)
            return

    elif message.text:
        if current_order.get(message.chat.id, {}).get('allow_manual'):
            clean_phone = re.sub(r'\D', '', message.text)
            if len(clean_phone) >= 9:
                if len(clean_phone) == 9: clean_phone = '998' + clean_phone
                if len(clean_phone) == 12 and clean_phone.startswith('998'):
                    formatted_phone = f"+{clean_phone[:3]} {clean_phone[3:5]} {clean_phone[5:8]} {clean_phone[8:10]} {clean_phone[10:12]}"
                    current_order[message.chat.id]['phone'] = formatted_phone
                    
                    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
                    markup.add("🍫 Shokoladli", "🍓 Qulupnayli", "🍦 Vanilli", "🍋 Limonli", "🎂 Plombir", "❌ Bekor qilish")
                    bot.send_message(message.chat.id, "✅ Raqam qabul qilindi.\n🍨 Qanday muzqaymoq xohlaysiz?", reply_markup=markup)
                    bot.register_next_step_handler(message, process_ice_cream)
                    return
            
            bot.send_message(message.chat.id, "❌ Noto'g'ri O'zbekiston raqami. Qaytadan to'g'ri yozing:")
            bot.register_next_step_handler(message, process_phone)
            return
        else:
            bot.send_message(
                message.chat.id, 
                "❌ Iltimos, raqamni qo'lda yozmang!\n"
                "Pastdagi <b>'📱 Telefon raqamni yuborish'</b> tugmasini bosing:",
                parse_mode='HTML'
            )
            bot.register_next_step_handler(message, process_phone)
            return

def process_ice_cream(message):
    if message.text == "❌ Bekor qilish": return cancel_order(message)
    current_order[message.chat.id]['type'] = message.text
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("📦 Dona", "⚖️ Kilogramm (kg)", "❌ Bekor qilish")
    bot.send_message(message.chat.id, f"Siz <b>{message.text}</b> tanladingiz.\nQanday o'lchovda?", reply_markup=markup, parse_mode='HTML')
    bot.register_next_step_handler(message, process_unit)

def process_unit(message):
    if message.text == "❌ Bekor qilish": return cancel_order(message)
    unit = "Dona" if "Dona" in message.text else "kg"
    current_order[message.chat.id]['unit'] = unit
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    markup.add("❌ Bekor qilish")
    if unit == "Dona":
        bot.send_message(message.chat.id, "Necha dona xohlaysiz? (Faqat raqam yozing):", reply_markup=markup)
    else:
        bot.send_message(message.chat.id, "Necha kilogramm xohlaysiz? (Faqat raqam yozing):", reply_markup=markup)
    bot.register_next_step_handler(message, process_quantity)

def process_quantity(message):
    if message.text == "❌ Bekor qilish": return cancel_order(message)
    qty_text = message.text.replace(',', '.').strip()
    try:
        val = float(qty_text)
        if val <= 0: raise ValueError
    except ValueError:
        bot.send_message(message.chat.id, "❌ Noto'g'ri! Iltimos, **faqat raqam** kiriting.")
        bot.register_next_step_handler(message, process_quantity)
        return

    current_order[message.chat.id]['qty'] = qty_text
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("💵 Naqd pul", "💳 Karta orqali", "❌ Bekor qilish")
    bot.send_message(message.chat.id, "To'lovni qanday amalga oshirasiz?", reply_markup=markup)
    bot.register_next_step_handler(message, process_payment)

def process_payment(message):
    if message.text == "❌ Bekor qilish": return cancel_order(message)
    current_order[message.chat.id]['payment'] = message.text
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(types.KeyboardButton("📍 Joylashuvni yuborish (Avtomat)", request_location=True), "❌ Bekor qilish")
    bot.send_message(
        message.chat.id, 
        "Manzilingizni yuboring (Faqat pastdagi tugma orqali):", 
        reply_markup=markup
    )
    bot.register_next_step_handler(message, process_location)

# 6. FAQAT TUGMA ORQALI LOKATSIYA QABUL QILISH
def process_location(message):
    try:
        if message.text == "❌ Bekor qilish": return cancel_order(message)
        
        # 1-holat: Agar haqiqatdan ham lokatsiya (GPS xarita) yuborgan bo'lsa
        if message.location:
            lat = message.location.latitude
            lon = message.location.longitude
            
            # O'zbekiston chegaralarini tekshirish
            if not (37.0 <= lat <= 45.6 and 56.0 <= lon <= 73.2):
                bot.send_message(message.chat.id, "❌ Uzr, lekin siz yuborgan joylashuv O'zbekiston hududidan tashqarida. Iltimos, to'g'ri manzil yuboring:")
                bot.register_next_step_handler(message, process_location)
                return

            map_link = f"https://maps.google.com/?q={lat},{lon}"
            location_text = f"<a href='{map_link}'>📍 Xaritada ko'rish</a>"
            
        # 2-holat: Agar mijoz o'jarlik qilib MATN yozib yuborgan bo'lsa
        else:
            bot.send_message(
                message.chat.id, 
                "❌ Manzilni qo'lda yozish mumkin emas!\n\n"
                "Iltimos, pastdagi <b>'📍 Joylashuvni yuborish'</b> tugmasini bosing:",
                parse_mode='HTML'
            )
            # Yana shu qadamga qaytarib qo'yamiz (Kutilaveradi)
            bot.register_next_step_handler(message, process_location)
            return

        # Lokatsiya to'g'ri bo'lsa, davom etamiz
        order_data = current_order.get(message.chat.id)
        if not order_data: return send_welcome(message)

        tg_user_name = message.from_user.first_name
        username = f"@{message.from_user.username}" if message.from_user.username else "Mavjud emas"
        receiver_name = order_data['receiver'] 
        current_time = get_uzbekistan_time().strftime("%Y-%m-%d %H:%M")

        if message.chat.id not in user_orders: user_orders[message.chat.id] = []
        user_orders[message.chat.id].append({
            "type": order_data['type'], "qty": order_data['qty'], "unit": order_data['unit'], 
            "date": current_time, "receiver": receiver_name
        })
        if message.chat.id in user_status: user_status[message.chat.id]['cancels'] = 0

        bot.send_message(message.chat.id, f"🎉 Rahmat! Buyurtmangiz qabul qilindi.", reply_markup=get_main_menu())
        
        if "Karta" in order_data['payment']:
            bot.send_message(message.chat.id, "💳 Karta: <code>8600 1234 5678 9012</code>\n(Egasi: Ism)", parse_mode='HTML')

        channel_text = (
            "🚨 <b>YANGI BUYURTMA!</b> 🍦\n\n"
            f"👤 <b>Qabul qiluvchi:</b> {receiver_name}\n"
            f"📱 <b>Buyurtmachi (Tg):</b> {tg_user_name} ({username})\n"
            f"📞 <b>Raqam:</b> {order_data['phone']}\n"
            f"🍨 <b>Muzqaymoq:</b> {order_data['type']}\n"
            f"⚖️ <b>Miqdori:</b> {order_data['qty']} ({order_data['unit']})\n"
            f"💰 <b>To'lov:</b> {order_data['payment']}\n"
            f"⏰ <b>Vaqti:</b> {current_time}\n"
            f"🏠 <b>Manzil:</b> {location_text}"
        )
        bot.send_message(CHANNEL_USERNAME, channel_text, parse_mode='HTML', disable_web_page_preview=True)

        bot.send_location(CHANNEL_USERNAME, lat, lon)
        del current_order[message.chat.id]

    except Exception as e:
        bot.send_message(message.chat.id, "Kechirasiz, xatolik yuz berdi. /start ni bosing.")

if __name__ == '__main__':
    bot.infinity_polling(timeout=10, long_polling_timeout=5, skip_pending=True)
