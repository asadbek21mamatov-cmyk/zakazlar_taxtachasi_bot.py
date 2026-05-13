import os
import re
import json
import base64
import logging
import requests
import telebot
from telebot import types
from datetime import datetime
import pytz
import random
import string

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

TOKEN = '8606446257:AAEflktYac20545qsk192Eh3B5109HHvhX4'
bot = telebot.TeleBot(TOKEN)

WEB_APP_URL = "https://botpy2.netlify.app"
CHANNEL_USERNAME = '@zakaz_taxtachasi'
TASHKENT_TZ = pytz.timezone('Asia/Tashkent')
ADMIN_ID = 6599495111

# ==========================================
# 🔧 GITHUB SOZLAMALARI
# ==========================================
from dotenv import load_dotenv
load_dotenv()
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
GITHUB_USER = 'asadbek21mamatov-cmyk'
GITHUB_REPO = 'zakazlar-taxtachasi'
GITHUB_FILE = 'mahsulotlar.json'
GITHUB_API = f'https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/contents/{GITHUB_FILE}'
RAW_URL = f'https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/main/{GITHUB_FILE}'

try:
    bot.set_chat_menu_button(None)
except Exception:
    pass

current_order = {}
active_orders = {}
admin_state = {}

# ==========================================
# 📦 GITHUB DAN MAHSULOTLARNI O'QISH/SAQLASH
# ==========================================
def github_mahsulotlar_yukla():
    """GitHub'dan mahsulotlar.json ni yuklash"""
    try:
        res = requests.get(RAW_URL + '?cache=' + str(random.randint(1, 999999)),
                          headers={'Cache-Control': 'no-cache'}, timeout=10)
        if res.status_code == 200:
            return res.json()
    except Exception as e:
        logging.error(f"GitHub'dan yuklashda xato: {e}")
    return []

def github_mahsulotlar_saqlа(mahsulotlar):
    """Mahsulotlarni GitHub'ga saqlash"""
    try:
        # Avval hozirgi faylning SHA sini olish (keyin yangilash uchun kerak)
        headers = {
            'Authorization': f'token {GITHUB_TOKEN}',
            'Content-Type': 'application/json'
        }
        res = requests.get(GITHUB_API, headers=headers, timeout=10)
        sha = res.json().get('sha', '') if res.status_code == 200 else ''

        # JSON ni base64 ga o'girish
        content = json.dumps(mahsulotlar, ensure_ascii=False, indent=2)
        encoded = base64.b64encode(content.encode('utf-8')).decode('utf-8')

        data = {
            'message': 'Ombor yangilandi (bot orqali)',
            'content': encoded,
            'sha': sha
        }

        put_res = requests.put(GITHUB_API, headers=headers, json=data, timeout=15)
        if put_res.status_code in [200, 201]:
            logging.info("GitHub'ga muvaffaqiyatli saqlandi")
            return True
        else:
            logging.error(f"GitHub saqlash xatosi: {put_res.status_code} — {put_res.text}")
            return False
    except Exception as e:
        logging.error(f"GitHub saqlashda xato: {e}")
        return False

def ombor_yukla():
    """Mahsulotlarni GitHub'dan yuklash"""
    mahsulotlar = github_mahsulotlar_yukla()
    if mahsulotlar:
        logging.info(f"GitHub'dan yuklandi: {len(mahsulotlar)} ta mahsulot")
        return mahsulotlar
    logging.warning("GitHub'dan yuklab bo'lmadi, bo'sh qaytdi")
    return []

# Botni ishga tushirganda yuklash
MAHSULOTLAR = ombor_yukla()

def mahsulot_topish(name):
    for m in MAHSULOTLAR:
        if m['name'] == name:
            return m
    return None

def ombor_get(name):
    m = mahsulot_topish(name)
    return m['stock'] if m else 0

def ombor_set(name, qty):
    for m in MAHSULOTLAR:
        if m['name'] == name:
            m['stock'] = qty
            return True
    return False

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
        markup.add(web_app_btn)
        markup.add(
            types.KeyboardButton("📦 Omborni ko'rish"),
            types.KeyboardButton("✏️ Omborni yangilash")
        )
        markup.add(
            types.KeyboardButton("➕ Yangi mahsulot qo'shish"),
            types.KeyboardButton("🗑 Mahsulot o'chirish")
        )
        bot.send_message(message.chat.id, "👋 Assalomu alaykum, Admin!\nNimani qilmoqchisiz?", reply_markup=markup)
    else:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
        markup.add(types.KeyboardButton("🛒 Do'konni ochish", web_app=types.WebAppInfo(url=WEB_APP_URL)))
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
    if not MAHSULOTLAR:
        bot.send_message(message.chat.id, "❌ Mahsulotlar yuklanmagan!")
        return
    text = "📦 <b>OMBORDAGI QOLDIQLAR:</b>\n\n"
    for m in MAHSULOTLAR:
        if m['stock'] <= 0:
            text += f"🔴 <s>{m['name']}</s> — TUGAGAN!\n"
        else:
            text += f"🟢 {m['name']} — {m['stock']} ta\n"
    bot.send_message(message.chat.id, text, parse_mode='HTML')


# ==========================================
# ✏️ OMBORNI YANGILASH
# ==========================================
@bot.message_handler(func=lambda m: m.text == "✏️ Omborni yangilash")
@bot.message_handler(commands=['yangilash'])
def ombor_yangilash_start(message):
    if not is_admin(message.chat.id):
        bot.send_message(message.chat.id, "❌ Faqat admin uchun!")
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    for m in MAHSULOTLAR:
        emoji = "🔴" if m['stock'] <= 0 else "🟢"
        markup.add(types.KeyboardButton(f"{emoji} {m['name']} ({m['stock']} ta)"))
    markup.add(types.KeyboardButton("🔙 Orqaga"))

    bot.send_message(message.chat.id, "📦 <b>Qaysi mahsulotni yangilamoqchisiz?</b>", reply_markup=markup, parse_mode='HTML')
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
        bot.send_message(message.chat.id, "❌ Ro'yxatdan tanlang!")
        return
    mahsulot_nomi = match.group(1)
    mahsulot = mahsulot_topish(mahsulot_nomi)
    if not mahsulot:
        bot.send_message(message.chat.id, "❌ Mahsulot topilmadi!")
        return

    admin_state[message.chat.id] = {'holat': 'miqdor_kiriting', 'mahsulot': mahsulot_nomi}
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🔙 Orqaga")
    bot.send_message(
        message.chat.id,
        f"✏️ <b>{mahsulot_nomi}</b>\nHozirgi miqdor: <b>{mahsulot['stock']} ta</b>\n\nYangi miqdorni kiriting:",
        reply_markup=markup, parse_mode='HTML'
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
        bot.send_message(message.chat.id, "❌ Faqat raqam kiriting!")
        return
    if yangi_miqdor < 0:
        bot.send_message(message.chat.id, "❌ Miqdor manfiy bo'lishi mumkin emas!")
        return

    mahsulot_nomi = admin_state[message.chat.id]['mahsulot']
    mahsulot = mahsulot_topish(mahsulot_nomi)
    eski_miqdor = mahsulot['stock']

    ombor_set(mahsulot_nomi, yangi_miqdor)
    admin_state.pop(message.chat.id, None)

    bot.send_message(message.chat.id, "⏳ GitHub'ga saqlanmoqda...")
    ok = github_mahsulotlar_saqlа(MAHSULOTLAR)

    if ok:
        bot.send_message(
            message.chat.id,
            f"✅ <b>Saqlandi! Sayt ~1 daqiqada yangilanadi.</b>\n\n"
            f"📦 {mahsulot_nomi}\n"
            f"🔄 {eski_miqdor} ta → 🆕 {yangi_miqdor} ta",
            parse_mode='HTML'
        )
    else:
        ombor_set(mahsulot_nomi, eski_miqdor)
        bot.send_message(message.chat.id, "❌ GitHub'ga saqlashda xato yuz berdi! Qaytadan urining.")

    send_welcome(message)


# ==========================================
# ➕ YANGI MAHSULOT QO'SHISH
# ==========================================
@bot.message_handler(func=lambda m: m.text == "➕ Yangi mahsulot qo'shish")
def yangi_mahsulot_start(message):
    if not is_admin(message.chat.id):
        bot.send_message(message.chat.id, "❌ Faqat admin uchun!")
        return
    admin_state[message.chat.id] = {'holat': 'yangi_nom'}
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🔙 Orqaga")
    bot.send_message(message.chat.id, "➕ <b>Yangi mahsulot qo'shish</b>\n\nMahsulot <b>nomini</b> kiriting:", reply_markup=markup, parse_mode='HTML')


@bot.message_handler(func=lambda m: isinstance(admin_state.get(m.chat.id), dict) and admin_state.get(m.chat.id, {}).get('holat') == 'yangi_nom')
def yangi_nom(message):
    if message.text == "🔙 Orqaga":
        admin_state.pop(message.chat.id, None)
        return send_welcome(message)
    admin_state[message.chat.id]['nom'] = message.text.strip()
    admin_state[message.chat.id]['holat'] = 'yangi_narx'
    bot.send_message(message.chat.id, f"✅ Nom: <b>{message.text.strip()}</b>\n\nNarxini kiriting (faqat raqam, so'mda):", parse_mode='HTML')


@bot.message_handler(func=lambda m: isinstance(admin_state.get(m.chat.id), dict) and admin_state.get(m.chat.id, {}).get('holat') == 'yangi_narx')
def yangi_narx(message):
    if message.text == "🔙 Orqaga":
        admin_state.pop(message.chat.id, None)
        return send_welcome(message)
    try:
        narx = int(message.text.strip())
    except ValueError:
        bot.send_message(message.chat.id, "❌ Faqat raqam kiriting! Masalan: 80000")
        return
    admin_state[message.chat.id]['narx'] = narx
    admin_state[message.chat.id]['holat'] = 'yangi_miqdor'
    bot.send_message(message.chat.id, f"✅ Narx: <b>{narx:,} so'm</b>\n\nOmbordagi miqdorini kiriting:", parse_mode='HTML')


@bot.message_handler(func=lambda m: isinstance(admin_state.get(m.chat.id), dict) and admin_state.get(m.chat.id, {}).get('holat') == 'yangi_miqdor')
def yangi_miqdor_fn(message):
    if message.text == "🔙 Orqaga":
        admin_state.pop(message.chat.id, None)
        return send_welcome(message)
    try:
        miqdor = int(message.text.strip())
    except ValueError:
        bot.send_message(message.chat.id, "❌ Faqat raqam kiriting!")
        return
    admin_state[message.chat.id]['miqdor'] = miqdor
    admin_state[message.chat.id]['holat'] = 'yangi_rasm'
    bot.send_message(message.chat.id, f"✅ Miqdor: <b>{miqdor} ta</b>\n\nRasm URL sini kiriting (https://... bilan boshlanadigan):\n\n💡 Rasm bo'lmasa 'yoq' deb yozing:", parse_mode='HTML')


@bot.message_handler(func=lambda m: isinstance(admin_state.get(m.chat.id), dict) and admin_state.get(m.chat.id, {}).get('holat') == 'yangi_rasm')
def yangi_rasm(message):
    if message.text == "🔙 Orqaga":
        admin_state.pop(message.chat.id, None)
        return send_welcome(message)
    rasm = message.text.strip() if message.text.strip() != 'yoq' else ''
    admin_state[message.chat.id]['rasm'] = rasm
    admin_state[message.chat.id]['holat'] = 'yangi_tavsif'
    bot.send_message(message.chat.id, "✅ Rasm saqlandi!\n\nMahsulot <b>tavsifini</b> kiriting:", parse_mode='HTML')


@bot.message_handler(func=lambda m: isinstance(admin_state.get(m.chat.id), dict) and admin_state.get(m.chat.id, {}).get('holat') == 'yangi_tavsif')
def yangi_tavsif(message):
    if message.text == "🔙 Orqaga":
        admin_state.pop(message.chat.id, None)
        return send_welcome(message)
    admin_state[message.chat.id]['tavsif'] = message.text.strip()
    admin_state[message.chat.id]['holat'] = 'yangi_ishlatish'
    bot.send_message(message.chat.id, "✅ Tavsif saqlandi!\n\nQo'llanilishi / Ishlatish usulini kiriting:", parse_mode='HTML')


@bot.message_handler(func=lambda m: isinstance(admin_state.get(m.chat.id), dict) and admin_state.get(m.chat.id, {}).get('holat') == 'yangi_ishlatish')
def yangi_ishlatish(message):
    if message.text == "🔙 Orqaga":
        admin_state.pop(message.chat.id, None)
        return send_welcome(message)

    state = admin_state[message.chat.id]
    yangi_id = max([m['id'] for m in MAHSULOTLAR], default=0) + 1

    yangi_mahsulot = {
        "id": yangi_id,
        "name": state['nom'],
        "price": state['narx'],
        "image": state['rasm'],
        "desc": state['tavsif'],
        "usage": message.text.strip(),
        "stock": state['miqdor']
    }

    MAHSULOTLAR.append(yangi_mahsulot)
    admin_state.pop(message.chat.id, None)

    bot.send_message(message.chat.id, "⏳ GitHub'ga saqlanmoqda...")
    ok = github_mahsulotlar_saqlа(MAHSULOTLAR)

    if ok:
        bot.send_message(
            message.chat.id,
            f"✅ <b>Yangi mahsulot qo'shildi! Sayt ~1 daqiqada yangilanadi.</b>\n\n"
            f"🆔 ID: {yangi_id}\n"
            f"📦 Nom: <b>{state['nom']}</b>\n"
            f"💰 Narx: <b>{state['narx']:,} so'm</b>\n"
            f"📊 Miqdor: <b>{state['miqdor']} ta</b>",
            parse_mode='HTML'
        )
    else:
        MAHSULOTLAR.pop()
        bot.send_message(message.chat.id, "❌ GitHub'ga saqlashda xato! Qaytadan urining.")

    send_welcome(message)


# ==========================================
# 🗑 MAHSULOT O'CHIRISH
# ==========================================
@bot.message_handler(func=lambda m: m.text == "🗑 Mahsulot o'chirish")
def mahsulot_ochirish_start(message):
    if not is_admin(message.chat.id):
        bot.send_message(message.chat.id, "❌ Faqat admin uchun!")
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    for m in MAHSULOTLAR:
        markup.add(types.KeyboardButton(f"🗑 {m['name']}"))
    markup.add(types.KeyboardButton("🔙 Orqaga"))

    bot.send_message(message.chat.id, "🗑 <b>Qaysi mahsulotni o'chirmoqchisiz?</b>", reply_markup=markup, parse_mode='HTML')
    admin_state[message.chat.id] = 'ochirish'


@bot.message_handler(func=lambda m: admin_state.get(m.chat.id) == 'ochirish')
def mahsulot_ochirish(message):
    if not is_admin(message.chat.id):
        return
    if message.text == "🔙 Orqaga":
        admin_state.pop(message.chat.id, None)
        return send_welcome(message)

    if not message.text.startswith("🗑 "):
        bot.send_message(message.chat.id, "❌ Ro'yxatdan tanlang!")
        return

    mahsulot_nomi = message.text[2:].strip()
    mahsulot = mahsulot_topish(mahsulot_nomi)
    if not mahsulot:
        bot.send_message(message.chat.id, "❌ Mahsulot topilmadi!")
        return

    # Tasdiqlash
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("✅ Ha, o'chir", callback_data=f"ochir_{mahsulot_nomi}"),
        types.InlineKeyboardButton("❌ Bekor", callback_data="ochir_bekor")
    )
    bot.send_message(
        message.chat.id,
        f"⚠️ <b>{mahsulot_nomi}</b> mahsulotini o'chirishni tasdiqlaysizmi?",
        reply_markup=markup, parse_mode='HTML'
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith('ochir_'))
def ochirish_tasdiqlash(call):
    if call.data == 'ochir_bekor':
        bot.edit_message_text("❌ Bekor qilindi.", call.message.chat.id, call.message.message_id)
        admin_state.pop(call.message.chat.id, None)
        send_welcome(call.message)
        return

    mahsulot_nomi = call.data[6:]
    mahsulot = mahsulot_topish(mahsulot_nomi)
    if not mahsulot:
        bot.answer_callback_query(call.id, "Mahsulot topilmadi!")
        return

    MAHSULOTLAR.remove(mahsulot)
    admin_state.pop(call.message.chat.id, None)

    bot.edit_message_text("⏳ GitHub'ga saqlanmoqda...", call.message.chat.id, call.message.message_id)
    ok = github_mahsulotlar_saqlа(MAHSULOTLAR)

    if ok:
        bot.send_message(call.message.chat.id, f"✅ <b>{mahsulot_nomi}</b> o'chirildi! Sayt ~1 daqiqada yangilanadi.", parse_mode='HTML')
    else:
        MAHSULOTLAR.append(mahsulot)
        bot.send_message(call.message.chat.id, "❌ GitHub'ga saqlashda xato! Qaytadan urining.")

    send_welcome(call.message)


# ==========================================
# 🛒 BUYURTMA QABUL/BEKOR
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
            mahsulot = mahsulot_topish(name)
            if mahsulot:
                mahsulot['stock'] -= item['qty']
        github_mahsulotlar_saqlа(MAHSULOTLAR)

        new_text = f"🟢 <b>QABUL QILINDI</b>\n\n{order['channel_msg']}"
        bot.edit_message_text(new_text, call.message.chat.id, call.message.message_id, parse_mode='HTML')
        bot.send_message(
            order['user_id'],
            f"🎉 <b>Xushxabar!</b>\nSizning <b>{order_id}</b> raqamli buyurtmangiz qabul qilindi!\n\n"
            f"📞 Muammo bo'lsa: @asadbek21mamatov",
            parse_mode='HTML'
        )
    elif action == 'reject':
        new_text = f"🔴 <b>BEKOR QILINDI</b>\n\n{order['channel_msg']}"
        bot.edit_message_text(new_text, call.message.chat.id, call.message.message_id, parse_mode='HTML')
        bot.send_message(
            order['user_id'],
            f"😔 <b>Kechirasiz!</b>\nSizning <b>{order_id}</b> raqamli buyurtmangiz bekor qilindi.\n\n"
            f"📞 Sababi uchun: @asadbek21mamatov",
            parse_mode='HTML'
        )

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
            bot.send_message(message.chat.id, "Savat bo'sh!")
            return

        for item in cart_data:
            qoldiq = ombor_get(item['name'])
            if item['qty'] > qoldiq:
                bot.send_message(
                    message.chat.id,
                    f"❌ <b>{item['name']}</b> omborda yetarli emas (Qoldiq: {qoldiq} ta).",
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
        summary += f"\n💰 <b>Jami: {total:,} so'm</b>\n\n"

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("❌ Bekor qilish")
        bot.send_message(
            message.chat.id,
            summary + "Qabul qiluvchining <b>Ism va Familiyasini</b> yozing:",
            reply_markup=markup, parse_mode='HTML'
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
        bot.send_message(message.chat.id, "❌ Faqat Ism va Familiya kiriting (2 ta so'z).")
        bot.register_next_step_handler(message, process_name)
        return
    current_order[message.chat.id]['receiver'] = f"{words[0].capitalize()} {words[1].capitalize()}"
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(types.KeyboardButton("📱 Telefon raqamni yuborish", request_contact=True), "❌ Bekor qilish")
    bot.send_message(message.chat.id, "Telefon raqamingizni yuboring:", reply_markup=markup)
    bot.register_next_step_handler(message, process_phone)


def process_phone(message):
    if message.text == "❌ Bekor qilish":
        return send_welcome(message)
    if message.contact:
        current_order[message.chat.id]['phone'] = message.contact.phone_number
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add("💵 Naqd pul", "💳 Karta orqali", "❌ Bekor qilish")
        bot.send_message(message.chat.id, "To'lov usulini tanlang:", reply_markup=markup)
        bot.register_next_step_handler(message, process_payment)
    else:
        bot.send_message(message.chat.id, "❌ Tugmani bosing!")
        bot.register_next_step_handler(message, process_phone)


def process_payment(message):
    if message.text == "❌ Bekor qilish":
        return send_welcome(message)
    if message.text not in ["💵 Naqd pul", "💳 Karta orqali"]:
        bot.send_message(message.chat.id, "❌ Tugmalardan foydalaning!")
        bot.register_next_step_handler(message, process_payment)
        return
    current_order[message.chat.id]['payment'] = message.text
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(types.KeyboardButton("📍 Joylashuvni yuborish", request_location=True), "❌ Bekor qilish")
    bot.send_message(message.chat.id, "Manzilingizni yuboring:", reply_markup=markup)
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
            f"<b>Buyurtma</b>\n\n"
            f"<b>ID:</b> {order_id}\n"
            f"<b>Vaqt:</b> {current_time}\n"
            f"<b>Mijoz:</b> {order['receiver']}\n"
            f"<b>Telefon:</b> {order['phone']}\n"
            f"<b>Turi:</b> Yetkazib berish ({order['payment']})\n"
            f"<b>Holati:</b> Kutilmoqda ⏳\n"
            f"➖➖➖➖➖➖➖➖➖➖\n"
            f"{cart_text}\n"
            f"➖➖➖➖➖➖➖➖➖➖\n"
            f"<b>Jami:</b> {total_sum:,} so'm"
        )

        active_orders[order_id] = {
            'user_id': message.chat.id,
            'channel_msg': channel_msg,
            'cart': order['cart']
        }

        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("❌ Bekor qilish", callback_data=f"reject_{order_id}"),
            types.InlineKeyboardButton("✅ Qabul qilish", callback_data=f"accept_{order_id}")
        )
        try:
            xabar = bot.send_message(CHANNEL_USERNAME, channel_msg, parse_mode='HTML', reply_markup=markup)
            bot.send_location(CHANNEL_USERNAME, message.location.latitude, message.location.longitude, reply_to_message_id=xabar.message_id)
        except Exception as e:
            logging.error(f"Kanal xatosi: {e}")

        if "Karta" in order['payment']:
            bot.send_message(message.chat.id, "💳 Karta: <code>8600 1234 5678 9012</code>", parse_mode='HTML')

        del current_order[message.chat.id]
        bot.send_message(
            message.chat.id,
            f"✅ <b>{order_id}</b> raqamli buyurtmangiz joylashtirildi. Tasdiqlanishini kuting.",
            parse_mode='HTML', reply_markup=types.ReplyKeyboardRemove()
        )
        send_welcome(message)
    else:
        bot.send_message(message.chat.id, "❌ Joylashuvni yuborish tugmasini bosing.")
        bot.register_next_step_handler(message, process_location)


if __name__ == '__main__':
    logging.info("Bot ishga tushdi!")
    bot.infinity_polling()
