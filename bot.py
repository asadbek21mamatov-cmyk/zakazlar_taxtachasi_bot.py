import os
import re
import json
import logging
import telebot
from telebot import types
from datetime import datetime
import pytz
import random
import string

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

TOKEN = '8606446257:AAEflktYac20545qsk192Eh3B5109HHvhX4'
bot = telebot.TeleBot(TOKEN)

WEB_APP_URL = "https://serene-torte-06a176.netlify.app"
CHANNEL_USERNAME = '@zakaz_taxtachasi'
TASHKENT_TZ = pytz.timezone('Asia/Tashkent')
ADMIN_ID = 6599495111
OMBOR_FILE = 'ombor.json'

try:
    bot.set_chat_menu_button(None)
except Exception as e:
    pass

current_order = {}
active_orders = {}
admin_state = {}  # Admin holati (qaysi mahsulotni yangilayapti)

# ==========================================
# 💾 OMBOR FAYLDAN O'QISH / SAQLASH
# ==========================================
DEFAULT_OMBOR = {
    "LEBELAGE Cleansing Foam": 100,
    "ILDONG Foodis HiMilk": 100,
    "Lagom Mini To'plami (Nabor)": 100,
    "Chanel Parfyumlar To'plami": 100,
    "Jo Malone London To'plami": 100,
    "Dior Ayollar Parfyumi To'plami": 100,
    "Hermes Mini Iforlar To'plami": 100,
    "MeLoSo 3 in 1 Collagen Cream": 100,
    "MeLoSo 3 in 1 Cica Cream": 100,
    "MeLoSo 3 in 1 Lacto Probio Cream": 100,
    "Melasma-X AHA BHA Foam Cleansing": 100,
    "Round Lab Mini To'plami": 100,
    "Feramonli Intim Atir": 100,
    "CC Cream": 100,
    "Snail Moisture Foot Cream": 100,
    "Brown Rice Cleansing Foam": 100,
    "Dr.G R.E.D Blemish Clear Soothing Cream": 100,
    "AXIS-Y Set Nabor (Toner, Ko'z kremi, Serum, Oyna)": 100
}

def ombor_yukla():
    if os.path.exists(OMBOR_FILE):
        try:
            with open(OMBOR_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for key, val in DEFAULT_OMBOR.items():
                    if key not in data:
                        data[key] = val
                return data
        except Exception as e:
            logging.error(f"Ombor faylini o'qishda xato: {e}")
    return DEFAULT_OMBOR.copy()

def ombor_saqlа(ombor):
    try:
        with open(OMBOR_FILE, 'w', encoding='utf-8') as f:
            json.dump(ombor, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.error(f"Ombor faylini saqlashda xato: {e}")

OMBOR = ombor_yukla()
logging.info(f"Ombor yuklandi: {len(OMBOR)} ta mahsulot")

# ==========================================

def get_uzbekistan_time():
    return datetime.now(TASHKENT_TZ)

def generate_order_id():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def is_admin(user_id):
    return user_id == ADMIN_ID


# ==========================================
# 🏠 START
# ==========================================
@bot.message_handler(commands=['start'])
def send_welcome(message):
    if is_admin(message.chat.id):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        web_app_btn = types.KeyboardButton("🛒 Do'konni ochish", web_app=types.WebAppInfo(url=WEB_APP_URL))
        ombor_btn = types.KeyboardButton("📦 Omborni ko'rish")
        yangilash_btn = types.KeyboardButton("✏️ Omborni yangilash")
        markup.add(web_app_btn)
        markup.add(ombor_btn, yangilash_btn)
        bot.send_message(
            message.chat.id,
            "👋 Assalomu alaykum, Admin!\nNimani qilmoqchisiz?",
            reply_markup=markup
        )
    else:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
        web_app_btn = types.KeyboardButton("🛒 Do'konni ochish", web_app=types.WebAppInfo(url=WEB_APP_URL))
        markup.add(web_app_btn)
        bot.send_message(
            message.chat.id,
            "👋 Assalomu alaykum! Do'konimizga xush kelibsiz.\nPastdagi tugmani bosib, mahsulotlar katalogini oching:",
            reply_markup=markup
        )


# ==========================================
# 📦 OMBOR KO'RISH
# ==========================================
@bot.message_handler(func=lambda m: m.text == "📦 Omborni ko'rish")
@bot.message_handler(commands=['ombor'])
def ombor_korsatish(message):
    text = "📦 <b>OMBORDAGI QOLDIQLAR:</b>\n\n"
    for name, qty in OMBOR.items():
        if qty <= 0:
            text += f"🔴 <s>{name}</s> — TUGAGAN!\n"
        else:
            text += f"🟢 {name} — {qty} ta\n"
    bot.send_message(message.chat.id, text, parse_mode='HTML')


# ==========================================
# ✏️ OMBORNI YANGILASH — INTERAKTIV
# ==========================================
@bot.message_handler(func=lambda m: m.text == "✏️ Omborni yangilash")
@bot.message_handler(commands=['yangilash'])
def ombor_yangilash_start(message):
    if not is_admin(message.chat.id):
        bot.send_message(message.chat.id, "❌ Bu funksiya faqat admin uchun!")
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    for name in OMBOR.keys():
        qty = OMBOR[name]
        emoji = "🔴" if qty <= 0 else "🟢"
        markup.add(types.KeyboardButton(f"{emoji} {name} ({qty} ta)"))
    markup.add(types.KeyboardButton("🔙 Orqaga"))

    bot.send_message(
        message.chat.id,
        "📦 <b>Qaysi mahsulotni yangilamoqchisiz?</b>\nQuyidagi ro'yxatdan tanlang:",
        reply_markup=markup,
        parse_mode='HTML'
    )
    admin_state[message.chat.id] = 'tanlash'


@bot.message_handler(func=lambda m: m.text == "🔙 Orqaga")
def orqaga(message):
    admin_state.pop(message.chat.id, None)
    send_welcome(message)


@bot.message_handler(func=lambda m: admin_state.get(m.chat.id) == 'tanlash')
def mahsulot_tanlash(message):
    if not is_admin(message.chat.id):
        return

    match = re.match(r'^[🟢🔴]\s(.+?)\s\(\d+ ta\)$', message.text)
    if not match:
        bot.send_message(message.chat.id, "❌ Iltimos, ro'yxatdan mahsulot tanlang!")
        return

    mahsulot_nomi = match.group(1)
    if mahsulot_nomi not in OMBOR:
        bot.send_message(message.chat.id, "❌ Mahsulot topilmadi! Qaytadan tanlang.")
        return

    admin_state[message.chat.id] = {'holat': 'miqdor_kiriting', 'mahsulot': mahsulot_nomi}

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    markup.add("🔙 Orqaga")

    bot.send_message(
        message.chat.id,
        f"✏️ <b>{mahsulot_nomi}</b>\n"
        f"Hozirgi miqdor: <b>{OMBOR[mahsulot_nomi]} ta</b>\n\n"
        f"Yangi miqdorni kiriting (faqat raqam):",
        reply_markup=markup,
        parse_mode='HTML'
    )


@bot.message_handler(func=lambda m: isinstance(admin_state.get(m.chat.id), dict) and admin_state.get(m.chat.id, {}).get('holat') == 'miqdor_kiriting')
def miqdor_kiriting(message):
    if not is_admin(message.chat.id):
        return

    if message.text == "🔙 Orqaga":
        admin_state[message.chat.id] = 'tanlash'
        ombor_yangilash_start(message)
        return

    try:
        yangi_miqdor = int(message.text.strip())
    except ValueError:
        bot.send_message(message.chat.id, "❌ Faqat raqam kiriting! Masalan: 50")
        return

    if yangi_miqdor < 0:
        bot.send_message(message.chat.id, "❌ Miqdor manfiy bo'lishi mumkin emas!")
        return

    mahsulot_nomi = admin_state[message.chat.id]['mahsulot']
    eski_miqdor = OMBOR[mahsulot_nomi]
    OMBOR[mahsulot_nomi] = yangi_miqdor
    ombor_saqlа(OMBOR)

    admin_state.pop(message.chat.id, None)

    bot.send_message(
        message.chat.id,
        f"✅ <b>Ombor yangilandi va saqlandi!</b>\n\n"
        f"📦 Mahsulot: <b>{mahsulot_nomi}</b>\n"
        f"🔄 Eski miqdor: <b>{eski_miqdor} ta</b>\n"
        f"🆕 Yangi miqdor: <b>{yangi_miqdor} ta</b>",
        parse_mode='HTML'
    )
    send_welcome(message)


# ==========================================
# 📋 BUYRUQ ORQALI TEZKOR YANGILASH
# /ombor_yangi CC Cream 50
# ==========================================
@bot.message_handler(commands=['ombor_yangi'])
def ombor_yangi_cmd(message):
    if not is_admin(message.chat.id):
        bot.send_message(message.chat.id, "❌ Bu buyruq faqat admin uchun!")
        return

    parts = message.text.strip().split()
    if len(parts) < 3:
        bot.send_message(
            message.chat.id,
            "❌ Noto'g'ri format!\n\n"
            "<b>To'g'ri foydalanish:</b>\n"
            "<code>/ombor_yangi Mahsulot Nomi 50</code>",
            parse_mode='HTML'
        )
        return

    try:
        yangi_miqdor = int(parts[-1])
    except ValueError:
        bot.send_message(message.chat.id, "❌ Oxirgi qiymat raqam bo'lishi kerak!\nMasalan: <code>/ombor_yangi CC Cream 50</code>", parse_mode='HTML')
        return

    if yangi_miqdor < 0:
        bot.send_message(message.chat.id, "❌ Miqdor manfiy bo'lishi mumkin emas!")
        return

    mahsulot_nomi = ' '.join(parts[1:-1])

    if mahsulot_nomi not in OMBOR:
        tavsiyalar = [name for name in OMBOR.keys() if mahsulot_nomi.lower() in name.lower()]
        xabar = f"❌ <b>{mahsulot_nomi}</b> — topilmadi!\n\n"
        if tavsiyalar:
            xabar += "🔍 <b>O'xshash mahsulotlar:</b>\n"
            for t in tavsiyalar:
                xabar += f"• <code>{t}</code>\n"
        else:
            xabar += "📋 Ro'yxat uchun: /ombor"
        bot.send_message(message.chat.id, xabar, parse_mode='HTML')
        return

    eski_miqdor = OMBOR[mahsulot_nomi]
    OMBOR[mahsulot_nomi] = yangi_miqdor
    ombor_saqlа(OMBOR)

    bot.send_message(
        message.chat.id,
        f"✅ <b>Saqlandi!</b>\n\n"
        f"📦 <b>{mahsulot_nomi}</b>\n"
        f"🔄 {eski_miqdor} ta → 🆕 {yangi_miqdor} ta",
        parse_mode='HTML'
    )


# ==========================================
# 🛒 ADMIN TUGMALARI — QABUL / BEKOR
# ==========================================
@bot.callback_query_handler(func=lambda call: call.data.startswith('accept_') or call.data.startswith('reject_'))
def handle_admin_action(call):
    action, order_id = call.data.split('_')
    order = active_orders.get(order_id)

    if not order:
        bot.answer_callback_query(call.id, "Bu buyurtma allaqachon ko'rib chiqilgan!", show_alert=True)
        return

    if action == 'accept':
        for item in order['cart']:
            name = item['name']
            if name in OMBOR:
                OMBOR[name] -= item['qty']
        ombor_saqlа(OMBOR)

        new_text = f"🟢 <b>QABUL QILINDI</b>\n\n{order['channel_msg']}"
        bot.edit_message_text(new_text, call.message.chat.id, call.message.message_id, parse_mode='HTML')

        mijozga_xabar = (
            f"🎉 <b>Xushxabar!</b>\n"
            f"Sizning <b>{order_id}</b> raqamli buyurtmangiz qabul qilindi va tayyorlanmoqda!\n\n"
            f"📞 Agar birorta muammo yuz bersa, admin bilan bog'laning: @asadbek21mamatov"
        )
        bot.send_message(order['user_id'], mijozga_xabar, parse_mode='HTML')

    elif action == 'reject':
        new_text = f"🔴 <b>BEKOR QILINDI</b>\n\n{order['channel_msg']}"
        bot.edit_message_text(new_text, call.message.chat.id, call.message.message_id, parse_mode='HTML')

        mijozga_xabar = (
            f"😔 <b>Kechirasiz!</b>\n"
            f"Sizning <b>{order_id}</b> raqamli buyurtmangiz bekor qilindi.\n\n"
            f"📞 Sababi haqida ma'lumot olish uchun admin bilan bog'laning: @asadbek21mamatov"
        )
        bot.send_message(order['user_id'], mijozga_xabar, parse_mode='HTML')

    del active_orders[order_id]


# ==========================================
# 🌐 SAYTDAN KELGAN ZAKAZ
# ==========================================
@bot.message_handler(content_types=['web_app_data'])
def handle_web_app_data(message):
    try:
        bot.delete_message(message.chat.id, message.message_id)
    except Exception:
        pass

    try:
        cart_data = json.loads(message.web_app_data.data)
        if not cart_data:
            bot.send_message(message.chat.id, "Savat bo'sh! Iltimos nimadir tanlang.")
            return

        for item in cart_data:
            name = item['name']
            qty = item['qty']
            qoldiq = OMBOR.get(name, 0)

            if qty > qoldiq:
                bot.send_message(
                    message.chat.id,
                    f"❌ Kechirasiz, <b>{name}</b> mahsuloti ayni vaqtda omborda yetarli emas (Qoldiq: {qoldiq} ta).\n"
                    f"Iltimos, do'konga kirib miqdorni kamaytiring yoki boshqa mahsulot tanlang.",
                    parse_mode='HTML'
                )
                return

        current_order[message.chat.id] = {'cart': cart_data}
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
            summary + "Rasmiylashtirishni boshlaymiz!\nIltimos, qabul qiluvchining <b>Ism va Familiyasini</b> yozing:",
            reply_markup=markup,
            parse_mode='HTML'
        )
        bot.register_next_step_handler(message, process_name)
    except Exception as e:
        logging.error(f"Xato: {e}")


# ==========================================
# 🚶 BUYURTMA QADAMLARI
# ==========================================
def process_name(message):
    if message.text == "❌ Bekor qilish":
        return send_welcome(message)
    words = re.sub(r'\s+', ' ', message.text.strip()).split()
    is_valid = len(words) == 2
    for w in words:
        if not w.replace("'", "").replace("`", "").isalpha():
            is_valid = False

    if not is_valid:
        bot.send_message(message.chat.id, "❌ Noto'g'ri! Faqat Ism va Familiya kiriting (aniq 2 ta so'z).")
        bot.register_next_step_handler(message, process_name)
        return

    current_order[message.chat.id]['receiver'] = f"{words[0].capitalize()} {words[1].capitalize()}"
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(types.KeyboardButton("📱 Telefon raqamni yuborish", request_contact=True), "❌ Bekor qilish")
    bot.send_message(message.chat.id, "Yaxshi! Endi telefon raqamingizni pastdagi tugma orqali yuboring:", reply_markup=markup)
    bot.register_next_step_handler(message, process_phone)


def process_phone(message):
    if message.text == "❌ Bekor qilish":
        return send_welcome(message)
    if message.contact:
        current_order[message.chat.id]['phone'] = message.contact.phone_number
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add("💵 Naqd pul", "💳 Karta orqali", "❌ Bekor qilish")
        bot.send_message(message.chat.id, "✅ Raqam qabul qilindi.\nTo'lovni qanday amalga oshirasiz?", reply_markup=markup)
        bot.register_next_step_handler(message, process_payment)
    else:
        bot.send_message(message.chat.id, "❌ Iltimos, raqamni qo'lda yozmang! Pastdagi tugmani bosing.")
        bot.register_next_step_handler(message, process_phone)


def process_payment(message):
    if message.text == "❌ Bekor qilish":
        return send_welcome(message)
    if message.text not in ["💵 Naqd pul", "💳 Karta orqali"]:
        bot.send_message(message.chat.id, "❌ Faqat tugmalardan foydalaning!")
        bot.register_next_step_handler(message, process_payment)
        return

    current_order[message.chat.id]['payment'] = message.text
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(types.KeyboardButton("📍 Joylashuvni yuborish", request_location=True), "❌ Bekor qilish")
    bot.send_message(message.chat.id, "Manzilingizni yuboring (Tugma orqali):", reply_markup=markup)
    bot.register_next_step_handler(message, process_location)


def process_location(message):
    if message.text == "❌ Bekor qilish":
        return send_welcome(message)
    if message.location:
        order = current_order[message.chat.id]
        current_time = get_uzbekistan_time().strftime("%d %b %Y %H:%M")
        order_id = generate_order_id()

        cart_text = ""
        total_sum = 0
        for item in order['cart']:
            cost = item['qty'] * item['price']
            total_sum += cost
            cart_text += f"{item['qty']} x {item['name']} — {cost:,}\n"

        channel_msg = (
            f"<b>Buyurtma</b>\n"
            f"<i>Do'koningiz Nomi</i>\n\n"
            f"<b>ID:</b> {order_id}\n"
            f"<b>Vaqt:</b> {current_time}\n"
            f"<b>Mijoz:</b> {order['receiver']}\n"
            f"<b>Telefon:</b> {order['phone']}\n"
            f"<b>Turi:</b> Yetkazib berish ({order['payment']})\n"
            f"<b>Holati:</b> Kutilmoqda ⏳\n"
            f"➖➖➖➖➖➖➖➖➖➖\n"
            f"<b>Mahsulotlar</b>\n\n"
            f"{cart_text}\n"
            f"➖➖➖➖➖➖➖➖➖➖\n"
            f"<b>Jami summa:</b> {total_sum:,} so'm"
        )

        active_orders[order_id] = {
            'user_id': message.chat.id,
            'channel_msg': channel_msg,
            'cart': order['cart']
        }

        markup = types.InlineKeyboardMarkup(row_width=2)
        btn_reject = types.InlineKeyboardButton("❌ Bekor qilish", callback_data=f"reject_{order_id}")
        btn_accept = types.InlineKeyboardButton("✅ Qabul qilish", callback_data=f"accept_{order_id}")
        markup.add(btn_reject, btn_accept)

        try:
            xabar = bot.send_message(CHANNEL_USERNAME, channel_msg, parse_mode='HTML', reply_markup=markup)
            bot.send_location(CHANNEL_USERNAME, message.location.latitude, message.location.longitude, reply_to_message_id=xabar.message_id)
        except Exception as e:
            logging.error(f"Xato: {e}")

        if "Karta" in order['payment']:
            bot.send_message(message.chat.id, "💳 Karta: <code>8600 1234 5678 9012</code>\n(Egasi: Ismingiz)", parse_mode='HTML')

        del current_order[message.chat.id]

        user_reply = f"Sizning <b>{order_id}</b> raqamli buyurtmangiz joylashtirildi. Iltimos, tasdiqlanishini kuting."
        bot.send_message(message.chat.id, user_reply, parse_mode='HTML', reply_markup=types.ReplyKeyboardRemove())
        send_welcome(message)
    else:
        bot.send_message(message.chat.id, "❌ Iltimos, joylashuvni yuborish tugmasini bosing.")
        bot.register_next_step_handler(message, process_location)


if __name__ == '__main__':
    logging.info("Bot ishga tushdi!")
    bot.infinity_polling()
