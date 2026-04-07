import os
import json
import time
import requests
from flask import Flask, request, jsonify
from datetime import datetime

app = Flask(__name__)

# ==================== الإعدادات ====================
INSTANCE_ID = os.environ.get("INSTANCE_ID", "7107565478")
API_TOKEN   = os.environ.get("API_TOKEN", "503485c7be7c41aa9ae7737ea65750bd7b2e1fd0d8f943d796")
BASE_URL    = f"https://api.green-api.com/waInstance{INSTANCE_ID}"

ADMIN_PHONE = os.environ.get("ADMIN_PHONE", "966554325828")
ORDERS_GROUP = "120363405278766872@g.us"

DATA_PATH   = os.environ.get("DATA_PATH", "/opt/render/project/data")
USERS_FILE  = os.path.join(DATA_PATH, "ai_users.json")

SILENCE_HOURS = 24  # ساعة صمت بعد تسجيل الطلب

# ==================== تخزين البيانات ====================
def load_users():
    os.makedirs(DATA_PATH, exist_ok=True)
    if not os.path.exists(USERS_FILE):
        return {}
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_users(data):
    os.makedirs(DATA_PATH, exist_ok=True)
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ==================== إرسال الرسائل ====================
def send_message(chat_id, text):
    url = f"{BASE_URL}/sendMessage/{API_TOKEN}"
    payload = {"chatId": chat_id, "message": text}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"خطأ في الإرسال: {e}")

def send_group_message(group_id, text):
    send_message(group_id, text)

# ==================== منطق البوت ====================
def handle_message(sender, message_type, text):
    users = load_users()
    now = time.time()

    # تجاهل رسائل القروبات
    if "@g.us" in sender:
        return

    user = users.get(sender, {"state": "new", "silence_until": 0})

    # فحص الصمت (24 ساعة بعد تسجيل الطلب)
    if user.get("silence_until", 0) > now:
        return  # البوت صامت، لا رد

    # إذا أرسل العميل صوت/صورة/ملصق/فيديو
    if message_type in ["imageMessage", "audioMessage", "voiceMessage",
                         "videoMessage", "stickerMessage", "documentMessage"]:
        send_message(sender,
            "عزيزي العميل 🙏\n"
            "الرجاء إرسال رسالة *نصية* تصف طلبك أو استفسارك."
        )
        return

    # المرحلة: عميل جديد أو عاد بعد 24 ساعة
    if user["state"] in ["new", "done"]:
        send_message(sender,
            "مرحباً بك في *مذكرة سلمان AI* 👋\n\n"
            "يسعدنا خدمتك!\n"
            "الرجاء إرسال وصف طلبك أو استفسارك وسنتواصل معك في أقرب وقت."
        )
        user["state"] = "waiting"
        users[sender] = user
        save_users(users)
        return

    # المرحلة: انتظار وصف الطلب
    if user["state"] == "waiting":
        if not text or len(text.strip()) < 3:
            send_message(sender,
                "الرجاء كتابة وصف واضح لطلبك بالنص. 📝"
            )
            return

        # تأكيد الاستلام للعميل
        send_message(sender,
            "✅ تم استلام طلبك بنجاح!\n\n"
            "سيتم التواصل معك في أقرب وقت إن شاء الله.\n"
            "شكراً لتواصلك مع *مذكرة سلمان AI* 🤝"
        )

        # إرسال الطلب لقروب الطلبات
        timestamp = datetime.now().strftime("%Y-%m-%d %I:%M %p")
        phone = sender.replace("@c.us", "")
        group_msg = (
            "📋 *طلب جديد — مذكرة سلمان AI*\n"
            "─────────────────\n"
            f"📱 العميل: +{phone}\n"
            f"🕐 الوقت: {timestamp}\n"
            f"📝 الطلب:\n{text.strip()}\n"
            "─────────────────"
        )
        send_group_message(ORDERS_GROUP, group_msg)

        # تفعيل الصمت 24 ساعة
        user["state"] = "done"
        user["silence_until"] = now + (SILENCE_HOURS * 3600)
        user["last_request"] = text.strip()
        users[sender] = user
        save_users(users)
        return

# ==================== Webhook ====================
@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.json
        if not data:
            return jsonify({"status": "empty"}), 200

        # تجاهل الرسائل الصادرة
        if data.get("typeWebhook") != "incomingMessageReceived":
            return jsonify({"status": "ignored"}), 200

        msg_data    = data.get("messageData", {})
        sender_data = data.get("senderData", {})
        sender      = sender_data.get("chatId", "")
        msg_type    = msg_data.get("typeMessage", "")

        # استخراج النص
        text = ""
        if msg_type == "textMessage":
            text = msg_data.get("textMessageData", {}).get("textMessage", "")
        elif msg_type == "extendedTextMessage":
            text = msg_data.get("extendedTextMessageData", {}).get("text", "")

        if sender:
            handle_message(sender, msg_type, text)

    except Exception as e:
        print(f"خطأ في Webhook: {e}")

    return jsonify({"status": "ok"}), 200

@app.route("/", methods=["GET"])
def index():
    return "مذكرة سلمان AI — Bot is running ✅", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
