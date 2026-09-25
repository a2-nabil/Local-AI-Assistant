from flask import Flask, request, jsonify
import requests

app = Flask(__name__)
AI_CORE_URL = "http://ai-core:8000/chat"

@app.route("/alexa", methods=["POST"])
def alexa_endpoint():
    data = request.get_json()
    
    # অ্যালেক্সার রিকোয়েস্ট টাইপ চেক
    req_type = data.get("request", {}).get("type")
    
    # স্কিল ওপেন করার সময় ডিফল্ট গ্রিটিং
    if req_type == "LaunchRequest":
        return jsonify({
            "version": "1.0",
            "response": {
                "outputSpeech": {
                    "type": "PlainText",
                    "text": "Local AI Core is online. What can I do for you?"
                },
                "shouldEndSession": False
            }
        })
    
    # ইউজার কোনো ইনস্ট্রাকশন দিলে (Intent Request)
    if req_type == "IntentRequest":
        user_spoken_query = data.get("request", {}).get("intent", {}).get("slots", {}).get("command", {}).get("value", "")
        
        if not user_spoken_query:
            # ফলব্যাক মেসেজ
            speech_text = "I didn't catch that command. Please repeat."
        else:
            try:
                # AI Core-এ রিকোয়েস্ট পাঠানো
                payload = {
                    "session_id": "alexa_user_session",
                    "message": user_spoken_query,
                    "has_image": False
                }
                res = requests.post(AI_CORE_URL, json=payload, timeout=60)
                if res.status_code == 200:
                    ai_reply = res.json().get("response", "Task completed.")
                    # ভয়েস আউটপুট যেন খুব বড় না হয় (অ্যালেক্সার জন্য অপ্টিমাইজড)
                    speech_text = ai_reply[:300]
                else:
                    speech_text = "Failed to communicate with AI Core."
            except Exception as e:
                speech_text = f"An error occurred: {str(e)}"
        
        return jsonify({
            "version": "1.0",
            "response": {
                "outputSpeech": {
                    "type": "PlainText",
                    "text": speech_text
                },
                "shouldEndSession": True
            }
        })

    return jsonify({"version": "1.0", "response": {"shouldEndSession": True}})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)