import os
import re
import json
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
WEB_APP_URL = "https://aquamarine-elianore-37.tiiny.site" # Sizning saytingiz

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

# Bosh menyu (Endi Web App tugmasi bilan)
def get_main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    # Web app tugmasini yaratamiz
    web_app_btn = types.KeyboardButton("🛒 Menyuni ochish", web_app=types.WebAppInfo(url=WEB_APP_URL))
    markup.add(web_app_btn, "📜 Zakaz tarixi")
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
    if check_ban(message.chat.id): return handle_banned_users(message)
    if message.chat.id in current_order: del current_order[message.chat.id]
    
    bot.send_message(
        message.chat.id, 
        "🍦 Assalomu alaykum! Shirin muzqaymoqlar botiga xush kelibsiz!\nPastdagi tugma orqali menyuni ochib, buyurtma bering:", 
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

@bot.message_handler(func=lambda message: message.text in ["📜 Zakaz tarixi", "❌ Bekor qilish"])
def handle_menu_clicks(message):
    if check_ban(message.chat.id): return handle_banned_users(message)

    if message.text == "📜 Zakaz tarixi":
        history = user_orders.get(message.chat.id, [])
        if not history:
            bot.send_message(message.chat.id, "Sizda hali buyurtmalar tarixi yo'q", reply_markup=get_main_menu())
        else:
            text = "<b>Sizning tarixingiz:</b>\n\n"
            for i, order in enumerate(history, 1):
                receiver = order.get('receiver', 'Noma\'lum')
                text += f"📦 <b>{i}-buyurtma</b> <i>({order['date']})</i> [Kimgaga: {receiver}]\n"
                for item in order['cart']:
                    text += f"  - {item['name']}: {item['qty']} ta\n"
                text += "\n"
            bot.send_message(message.chat.id, text, parse_mode='HTML', reply_markup=get_main_menu())
            
    elif message.text == "❌ Bekor qilish":
        cancel_order(message)

# 0. YANGA QADAM: WEB APP DAN MA'LUMOT QABUL QILISH
@bot.message_handler(content_types=['web_app_data'])
def handle_web_app_data(message):
    if check_ban(message.chat.id): return handle_banned_users(message)
    
    try:
        # Saytdan kelgan JSON ma'lumotni o'qiymiz
        cart_data = json.loads(message.web_app_data.data)
        
        if not cart_data:
            bot.send_message(message.chat.id, "Savat bo'sh! Iltimos nimadir tanlang.")
            return

        current_order[message.chat.id] = {'cart': cart_data, 'allow_manual': False}
        
        # Mijozga nimalar tanlaganini chiroyli qilib ko'rsatamiz
        summary = "🛒 <b>Sizning savatingiz:</b>\n\n"
        total = 0
        for item in cart_data:
            cost = item['qty'] * item['price']
            total += cost
            summary += f"▪️ {item['name']} - {item['qty']} dona ({cost:,} so'm)\n"
        summary += f"\n💰 <b>Jami summa: {total:,} so'm</b>\n\n"

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
        markup.add("❌ Bekor qilish")
        bot.send_message(
            message.chat.id, 
            summary + "Boshladik! Iltimos, muzqaymoqni qabul qilib oluvchining <b>Ism va Familiyasini</b> yozib yuboring:", 
            reply_markup=markup, parse_mode='HTML'
        )
        bot.register_next_step_handler(message, process_name)
    except Exception as e:
        logging.error(f"Xato: {e}")

# 1. ISM FAMILIYANI QATTIQ TEKSHIRISH
def is_realistic_name(word):
    word_lower = word.lower()
    has_vowel = any(v in word_lower for v in "aeiouy")
    if not has_vowel: return False
    if re.search(r'(.)\1\1', word_lower): return False
    if re.search(r'[^aeiouy`\' ]{5,}', word_lower): return False
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
            if not alpha_word.isalpha() or len(alpha_word) < 3: is_valid = False
            elif not is_realistic_name(alpha_word): is_valid = False
                
    if not is_valid:
        bot.send_message(
            message.chat.id, 
            "❌ Kiritilgan ism haqiqiyga o'xshamayapti!\nIltimos, <b>faqat haqiqiy Ism va Familiya</b> kiriting (aniq 2 ta so'z).",
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

# 2. RAQAM TEKSHIRUVI
def process_phone(message):
    if message.text == "❌ Bekor qilish": return cancel_order(message)
    
    if message.contact:
        phone = message.contact.phone_number
        clean_phone = re.sub(r'\D', '', phone)
        
        if clean_phone.startswith('998') and len(clean_phone) == 12:
            formatted_phone = f"+{clean_phone[:3]} {clean_phone[3:5]} {clean_phone[5:8]} {clean_phone[8:10]} {clean_phone[10:12]}"
            current_order[message.chat.id]['phone'] = formatted_phone
            
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
            markup.add("💵 Naqd pul", "💳 Karta orqali", "❌ Bekor qilish")
            bot.send_message(message.chat.id, "✅ Raqam qabul qilindi.\nTo'lovni qanday amalga oshirasiz?", reply_markup=markup)
            bot.register_next_step_handler(message, process_payment)
            return
        else:
            current_order[message.chat.id]['allow_manual'] = True
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
            markup.add("❌ Bekor qilish")
            bot.send_message(
                message.chat.id, 
                "⚠️ Raqamingiz chet elga tegishli ekan. Iltimos, O'zbekiston raqamingizni qo'lda yozing:",
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
                    markup.add("💵 Naqd pul", "💳 Karta orqali", "❌ Bekor qilish")
                    bot.send_message(message.chat.id, "✅ Raqam qabul qilindi.\nTo'lovni qanday amalga oshirasiz?", reply_markup=markup)
                    bot.register_next_step_handler(message, process_payment)
                    return
            
            bot.send_message(message.chat.id, "❌ Noto'g'ri O'zbekiston raqami. Qaytadan to'g'ri yozing:")
            bot.register_next_step_handler(message, process_phone)
            return
        else:
            bot.send_message(
                message.chat.id, 
                "❌ Iltimos, raqamni qo'lda yozmang!\nPastdagi <b>'📱 Telefon raqamni yuborish'</b> tugmasini bosing:",
                parse_mode='HTML'
            )
            bot.register_next_step_handler(message, process_phone)
            return

# 3. TO'LOV
def process_payment(message):
    if message.text == "❌ Bekor qilish": return cancel_order(message)
    
    if message.text not in ["💵 Naqd pul", "💳 Karta orqali"]:
        bot.send_message(message.chat.id, "❌ Iltimos, faqat 'Naqd pul' yoki 'Karta orqali' tugmasini bosing!")
        bot.register_next_step_handler(message, process_payment)
        return

    current_order[message.chat.id]['payment'] = message.text
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(types.KeyboardButton("📍 Joylashuvni yuborish (Avtomat)", request_location=True), "❌ Bekor qilish")
    bot.send_message(message.chat.id, "Manzilingizni yuboring (Faqat pastdagi tugma orqali):", reply_markup=markup)
    bot.register_next_step_handler(message, process_location)

# 4. LOKATSIYA VA ZAKAZNI YAKUNLASH
def process_location(message):
    try:
        if message.text == "❌ Bekor qilish": return cancel_order(message)
        
        if message.location:
            lat = message.location.latitude
            lon = message.location.longitude
            
            if not (37.0 <= lat <= 45.6 and 56.0 <= lon <= 73.2):
                bot.send_message(message.chat.id, "❌ Uzr, lekin joylashuv O'zbekiston hududidan tashqarida.")
                bot.register_next_step_handler(message, process_location)
                return

            map_link = f"https://maps.google.com/?q={lat},{lon}"
            location_text = f"<a href='{map_link}'>📍 Xaritada ko'rish</a>"
            
        else:
            bot.send_message(message.chat.id, "❌ Manzilni qo'lda yozish mumkin emas! Tugmani bosing:")
            bot.register_next_step_handler(message, process_location)
            return

        order_data = current_order.get(message.chat.id)
        if not order_data: return send_welcome(message)

        tg_user_name = message.from_user.first_name
        username = f"@{message.from_user.username}" if message.from_user.username else "Mavjud emas"
        receiver_name = order_data['receiver'] 
        current_time = get_uzbekistan_time().strftime("%Y-%m-%d %H:%M")

        # Savatni kanal formatiga o'tkazish
        cart_details = ""
        total_price = 0
        for item in order_data['cart']:
            item_total = item['qty'] * item['price']
            total_price += item_total
            cart_details += f"  🔹 {item['name']} - {item['qty']} ta ({item_total:,} so'm)\n"

        if message.chat.id not in user_orders: user_orders[message.chat.id] = []
        user_orders[message.chat.id].append({
            "cart": order_data['cart'], "date": current_time, "receiver": receiver_name
        })
        if message.chat.id in user_status: user_status[message.chat.id]['cancels'] = 0

        bot.send_message(message.chat.id, f"🎉 Rahmat! Buyurtmangiz qabul qilindi.", reply_markup=get_main_menu())
        
        if "Karta" in order_data['payment']:
            bot.send_message(message.chat.id, "💳 Karta: <code>4916 9903 2004 8603</code>\n(Egasi: Ism)", parse_mode='HTML')

        channel_text = (
            "🚨 <b>YANGI BUYURTMA (Web App)!</b> 🍦\n\n"
            f"👤 <b>Qabul qiluvchi:</b> {receiver_name}\n"
            f"📱 <b>Buyurtmachi:</b> {tg_user_name} ({username})\n"
            f"📞 <b>Raqam:</b> {order_data['phone']}\n\n"
            f"🛒 <b>Savat:</b>\n{cart_details}"
            f"💰 <b>Jami To'lov:</b> {total_price:,} so'm ({order_data['payment']})\n\n"
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
