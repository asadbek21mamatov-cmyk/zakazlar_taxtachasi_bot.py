import os
import re
import logging
import telebot
from telebot import types
from datetime import datetime, timedelta

# Loglarni sozlash
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

TOKEN = os.getenv('BOT_TOKEN', '8787588894:AAHo5YdG3H_klIcxmjtKcOj5I-Va0e6sZyI')
bot = telebot.TeleBot(TOKEN)
CHANNEL_USERNAME = '@zakaz_taxtachasi'

user_orders = {}
current_order = {}
user_status = {}

def check_ban(chat_id):
    if chat_id in user_status and user_status[chat_id]['ban_until']:
        if datetime.now() < user_status[chat_id]['ban_until']:
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
        user_status[chat_id]['ban_until'] = datetime.now() + timedelta(hours=1)
        return True 
    return False

def get_main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🛒 Yangi buyurtma", "📜 Zakaz tarixi")
    return markup

@bot.message_handler(func=lambda message: check_ban(message.chat.id))
def handle_banned_users(message):
    ban_time = user_status[message.chat.id]['ban_until']
    left = ban_time - datetime.now()
    minutes = int(left.total_seconds() / 60)
    bot.send_message(
        message.chat.id, 
        f"🚫 <b>Siz bloklangansiz!</b>\n\n"
        f"Siz ketma-ket 3 marta buyurtmani bekor qildingiz. "
        f"1 soatga bloklandingiz.\n⏳ Qolgan vaqt: taxminan {minutes} daqiqa.",
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
            f"Buyurtma bekor qilindi.\n⚠️ <i>Ogohlantirish: Siz {cancels}/3 marta bekor qildingiz. 3 marta bo'lsa, 1 soatga bloklanasiz.</i>", 
            reply_markup=get_main_menu(), parse_mode='HTML'
        )

@bot.message_handler(func=lambda message: message.text in ["🛒 Yangi buyurtma", "📜 Zakaz tarixi", "❌ Bekor qilish"])
def handle_menu_clicks(message):
    if check_ban(message.chat.id):
        return handle_banned_users(message)

    if message.text == "📜 Zakaz tarixi":
        history = user_orders.get(message.chat.id, [])
        if not history:
            bot.send_message(message.chat.id, "Sizda hali buyurtmalar tarixi yo'q 😔", reply_markup=get_main_menu())
        else:
            text = "<b>Sizning tarixingiz:</b>\n\n"
            for i, order in enumerate(history, 1):
                text += f"{i}. <b>{order['type']}</b> - {order['qty']} {order['unit']} <i>({order['date']})</i>\n"
            bot.send_message(message.chat.id, text, parse_mode='HTML', reply_markup=get_main_menu())
            
    elif message.text == "❌ Bekor qilish":
        cancel_order(message)
        
    elif message.text == "🛒 Yangi buyurtma":
        current_order[message.chat.id] = {}
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add(types.KeyboardButton("📱 Telefon raqamni yuborish", request_contact=True))
        markup.add("❌ Bekor qilish")
        bot.send_message(message.chat.id, "Boshladik! Telefon raqamingizni yuboring:", reply_markup=markup)
        bot.register_next_step_handler(message, process_phone)

# 1. Raqam
def process_phone(message):
    if message.text == "❌ Bekor qilish": return cancel_order(message)
    phone = message.contact.phone_number if message.contact else message.text
    clean_phone = re.sub(r'\D', '', phone) if phone else ""
    if len(clean_phone) >= 9:
        if len(clean_phone) == 9: clean_phone = '998' + clean_phone
        formatted_phone = f"+{clean_phone[:3]} {clean_phone[3:5]} {clean_phone[5:8]} {clean_phone[8:10]} {clean_phone[10:12]}"
        current_order[message.chat.id]['phone'] = formatted_phone
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add("🍫 Shokoladli", "🍓 Qulupnayli", "🍦 Vanilli", "🍋 Limonli", "🎂 Plombir", "❌ Bekor qilish")
        bot.send_message(message.chat.id, "✅ Qabul qilindi.\n🍨 Qanday muzqaymoq xohlaysiz?", reply_markup=markup)
        bot.register_next_step_handler(message, process_ice_cream)
    else:
        bot.send_message(message.chat.id, "❌ Noto'g'ri raqam. Qaytadan kiriting:")
        bot.register_next_step_handler(message, process_phone)

# 2. Muzqaymoq turi
def process_ice_cream(message):
    if message.text == "❌ Bekor qilish": return cancel_order(message)
    current_order[message.chat.id]['type'] = message.text
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("📦 Dona", "⚖️ Kilogramm (kg)", "❌ Bekor qilish")
    bot.send_message(message.chat.id, f"Siz <b>{message.text}</b> tanladingiz.\nQanday o'lchovda?", reply_markup=markup, parse_mode='HTML')
    bot.register_next_step_handler(message, process_unit)

# 3. O'lchov
def process_unit(message):
    if message.text == "❌ Bekor qilish": return cancel_order(message)
    unit = "Dona" if "Dona" in message.text else "kg"
    current_order[message.chat.id]['unit'] = unit
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    markup.add("❌ Bekor qilish")
    if unit == "Dona":
        bot.send_message(message.chat.id, "Necha dona xohlaysiz? (Faqat raqam yozing, masalan: 10):", reply_markup=markup)
    else:
        bot.send_message(message.chat.id, "Necha kilogramm xohlaysiz? (Faqat raqam yozing, masalan: 1.5):", reply_markup=markup)
    bot.register_next_step_handler(message, process_quantity)

# 4. Miqdor (HARFLAR TAQIQLANDI)
def process_quantity(message):
    if message.text == "❌ Bekor qilish": return cancel_order(message)
    
    # Kiritilgan matnni raqam ekanligini tekshiramiz
    qty_text = message.text.replace(',', '.').strip() # Vergulni nuqtaga almashtiramiz (1,5 -> 1.5)
    try:
        val = float(qty_text) # Agar bu yerda harf bo'lsa, xatolik berib except blokiga o'tadi
        if val <= 0:
            raise ValueError
    except ValueError:
        bot.send_message(message.chat.id, "❌ Noto'g'ri! Iltimos, **faqat raqam** kiriting (harflarsiz).\nMasalan: 2 yoki 1.5:")
        # Xato qilsa yana shu funksiyani o'ziga qaytaramiz
        bot.register_next_step_handler(message, process_quantity)
        return

    # Agar raqam to'g'ri bo'lsa, xotiraga yozamiz
    current_order[message.chat.id]['qty'] = qty_text

    # YANGI QADAM: To'lov usulini so'rash
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("💵 Naqd pul", "💳 Karta orqali", "❌ Bekor qilish")
    bot.send_message(message.chat.id, "To'lovni qanday amalga oshirasiz?", reply_markup=markup)
    bot.register_next_step_handler(message, process_payment)

# 5. To'lov usuli
def process_payment(message):
    if message.text == "❌ Bekor qilish": return cancel_order(message)
    
    current_order[message.chat.id]['payment'] = message.text
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(types.KeyboardButton("📍 Joylashuvni yuborish (Avtomat)", request_location=True), "❌ Bekor qilish")
    bot.send_message(message.chat.id, "Manzilingizni yuboring (Tugmani bosing yoki yozing):", reply_markup=markup)
    bot.register_next_step_handler(message, process_location)

# 6. Lokatsiya va Yakunlash
def process_location(message):
    try:
        if message.text == "❌ Bekor qilish": return cancel_order(message)
        
        if message.location:
            map_link = f"https://maps.google.com/?q={message.location.latitude},{message.location.longitude}"
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

        if message.chat.id not in user_orders: user_orders[message.chat.id] = []
        user_orders[message.chat.id].append({
            "type": order_data['type'], "qty": order_data['qty'], "unit": order_data['unit'], "date": current_time
        })

        if message.chat.id in user_status: user_status[message.chat.id]['cancels'] = 0

        # Mijozga yuboriladigan tasdiq xabari
        bot.send_message(message.chat.id, f"🎉 Rahmat, {user_name}! Buyurtmangiz qabul qilindi.\nKuryer tez orada yetib boradi.", reply_markup=get_main_menu())
        
        # Agar karta tanlagan bo'lsa karta raqam tashlaymiz
        if "Karta" in order_data['payment']:
            bot.send_message(
                message.chat.id, 
                "💳 To'lov uchun karta raqamimiz:\n\n"
                "<code>8600 1234 5678 9012</code>\n"  # Shu yerga o'z karta raqamingizni yozing
                "(Egasi: Ismingizni Yozing)\n\n"
                "Iltimos, to'lovni amalga oshiring.", 
                parse_mode='HTML'
            )

        # Kanalga yuboriladigan matn
        channel_text = (
            "🚨 <b>YANGI BUYURTMA!</b> 🍦\n\n"
            f"👤 <b>Mijoz:</b> {user_name} ({username})\n"
            f"📞 <b>Raqam:</b> {order_data['phone']}\n"
            f"🍨 <b>Muzqaymoq:</b> {order_data['type']}\n"
            f"⚖️ <b>Miqdori:</b> {order_data['qty']} ({order_data['unit']})\n"
            f"💰 <b>To'lov turi:</b> {order_data['payment']}\n"
            f"⏰ <b>Vaqti:</b> {current_time}\n"
            f"🏠 <b>Manzil:</b> {location_text}"
        )
        bot.send_message(CHANNEL_USERNAME, channel_text, parse_mode='HTML', disable_web_page_preview=True)

        if message.location: bot.send_location(CHANNEL_USERNAME, message.location.latitude, message.location.longitude)
        del current_order[message.chat.id]

    except Exception as e:
        logging.error(f"Xatolik: {e}")
        bot.send_message(message.chat.id, "Kechirasiz, xatolik yuz berdi. /start ni bosing.")

if __name__ == '__main__':
    logging.info("Muzqaymoq boti ishga tushdi...")
    bot.infinity_polling(timeout=10, long_polling_timeout=5, skip_pending=True)
