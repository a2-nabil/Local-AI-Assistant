import os
import telebot
import requests
import base64

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ALLOWED_USER_ID = int(os.getenv("ALLOWED_USER_ID", 0))
AI_CORE_URL = "http://ai-core:8000/chat"

bot = telebot.TeleBot(BOT_TOKEN)

# মডেল সম্পর্কিত প্রশ্ন কি না তা চেক করার কিওয়ার্ড
MODEL_QUERY_KEYWORDS = [
    "what model", "which model", "model name", "current model", 
    "kon model", "model ki", "running model"
]

@bot.message_handler(content_types=['text', 'photo'])
def handle_message(message):
    user_id = message.from_user.id
    
    if user_id != ALLOWED_USER_ID:
        bot.reply_to(message, "⛔ Access Denied.")
        return

    # কাস্টম ওয়েটিং মেসেজ
    waiting_msg = bot.reply_to(message, "🍯 Honey is cooking for you...")

    payload = {
        "session_id": str(user_id),
        "message": "",
        "has_image": False,
        "image_base64": None
    }

    try:
        user_text = ""
        if message.content_type == 'photo':
            file_id = message.photo[-1].file_id
            file_info = bot.get_file(file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            payload["image_base64"] = base64.b64encode(downloaded_file).decode('utf-8')
            payload["has_image"] = True
            user_text = message.caption if message.caption else "Analyze this image and describe what you see."
        else:
            user_text = message.text

        payload["message"] = user_text

        response = requests.post(AI_CORE_URL, json=payload)
        
        if response.status_code == 200:
            result = response.json()
            used_model = result.get("used_model", "Unknown")
            ai_response = result.get("response", "")

            # ইউজার মডেলের নাম জানতে চেয়েছে কি না চেক করা
            asked_for_model = any(kw in user_text.lower() for kw in MODEL_QUERY_KEYWORDS)

            if asked_for_model:
                final_reply = f"🤖 I am currently running on **{used_model}**.\n\n{ai_response}"
            else:
                final_reply = ai_response

            bot.reply_to(message, final_reply)
        else:
            bot.reply_to(message, f"❌ Honey encountered an error: {response.status_code}")

    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")
    finally:
        # প্রসেসিং মেসেজটি ডিলিট করে দেওয়া (ক্লিন চ্যাট ইন্টারফেসের জন্য)
        try:
            bot.delete_message(message.chat.id, waiting_msg.message_id)
        except Exception:
            pass

print("Honey is online and listening...")
bot.polling()