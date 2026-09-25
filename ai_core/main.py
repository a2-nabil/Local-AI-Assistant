import base64
import os
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
import redis
from interpreter import interpreter

app = FastAPI()

# Redis কানেকশন (Docker Compose নেটওয়ার্কের ওপর ভিত্তি করে)
redis_client = redis.Redis(host='redis-db', port=6379, decode_responses=True)

# মডেল কনফিগারেশন
MODELS = {
    "vision": "minicpm-v",
    "fast": "qwen2.5-coder:7b",
    "heavy": "codestral:22b",
}

class ChatRequest(BaseModel):
    session_id: str
    message: str
    has_image: Optional[bool] = False
    image_base64: Optional[str] = None

# অটো মডেল রাউটিং লজিক
def select_best_model(message: str, has_image: bool) -> str:
    if has_image:
        return MODELS["vision"]

    lower_msg = message.lower()
    if "codestral" in lower_msg:
        return MODELS["heavy"]
    
    heavy_keywords = ["architecture", "system design", "refactor", "complex", "optimize"]
    if len(message) > 500 or any(kw in lower_msg for kw in heavy_keywords):
        return MODELS["heavy"]
    
    return MODELS["fast"]

@app.post("/chat")
async def chat_endpoint(req: ChatRequest):
    user_query = req.message.strip()
    selected_model = select_best_model(user_query, req.has_image)

    # Open Interpreter কনফিগারেশন
    interpreter.llm.model = f"ollama/{selected_model}"
    interpreter.llm.api_base = "http://host.docker.internal:11434"
    interpreter.auto_run = True

    try:
        # যদি ইমেজ থাকে, তবে ভিশন মডেলের জন্য Base64 ইমেজ হ্যান্ডেল করা
        if req.has_image and req.image_base64:
            image_bytes = base64.b64decode(req.image_base64)
            temp_img_path = f"/tmp/{req.session_id}_img.jpg"
            with open(temp_img_path, "wb") as f:
                f.write(image_bytes)
            
            # ভিশন প্রম্পট রান করা
            response = interpreter.chat(f"{user_query} {temp_img_path}")
        else:
            response = interpreter.chat(user_query)

        ai_response = "".join([item.get('content', '') for item in response if 'content' in item])

    except Exception as e:
        ai_response = f"Error executing task: {str(e)}"

    return {
        "status": "success",
        "used_model": selected_model,
        "response": ai_response
    }