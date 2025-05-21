from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import requests
import re

app = FastAPI()

GEMINI_API_KEY = "AIzaSyDD8QW1BggDVVMLteDygHCHrD6Ff9Dy0e8"
GEMINI_MODEL = "gemini-2.0-flash"
CONFIRM_PAGE_ID = "c2bd0e45-a3c4-4ec4-b54b-013e61b41207"

def clean_and_trim_text(text: str) -> str:
    text = re.sub(r"[*_~`]", "", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    words = text.strip().split()
    return text if len(words) < 30 else " ".join(words[:40])

async def handle_webhook_logic(body: dict):
    session_params = body.get("sessionInfo", {}).get("parameters", {})
    user_input = body.get("text", "").lower().strip()

    full_page_path = body.get("pageInfo", {}).get("currentPage", "")
    current_page_id = full_page_path.split("/")[-1] if full_page_path else "Unknown"
    last_page = session_params.get("last_page")
    update_last_page = full_page_path if current_page_id != CONFIRM_PAGE_ID else last_page

    reply = ""
    target_page = None

    if current_page_id == CONFIRM_PAGE_ID:
        if user_input in ["yes", "yeah", "yep", "sure"]:
            if last_page and isinstance(last_page, str):
                reply = "Okay, taking you back."
                target_page = last_page
            else:
                reply = "I don’t remember where we were. Let’s start over."
        elif user_input in ["no", "nope", "nah"]:
            reply = "Alright. Let me know if you need anything else."
        else:
            reply = "Please say 'yes' to go back or 'no' to cancel."
    else:
        if not user_input:
            user_input = session_params.get("fallback-input", "Hello")

        gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": user_input}]
                }
            ]
        }

        try:
            response = requests.post(gemini_url, json=payload)
            response.raise_for_status()
            gemini_raw = response.json()["candidates"][0]["content"]["parts"][0]["text"]
            cleaned = clean_and_trim_text(gemini_raw)
        except Exception:
            cleaned = "Sorry, I couldn't find an answer."

        reply = f"{cleaned}"

    # 🧠 Reset loop-causing parameters if value == user input
    reset_params = {
        key: None
        for key, val in session_params.items()
        if isinstance(val, str) and val.strip().lower() == user_input
    }

    # ✅ Final response with reset + last_page tracking
    response_data = {
        "fulfillment_response": {
            "messages": [{"text": {"text": [reply]}}]
        },
        "session_info": {
            "parameters": {
                **reset_params,
                "last_response": reply,
                "last_page": update_last_page
            }
        }
    }

    if target_page:
        response_data["target_page"] = target_page

    return JSONResponse(content=response_data)

@app.post("/webhook")
async def webhook(request: Request):
    body = await request.json()
    return await handle_webhook_logic(body)

@app.post("/{full_path:path}")
async def catch_all_post(full_path: str, request: Request):
    body = await request.json()
    return await handle_webhook_logic(body)
