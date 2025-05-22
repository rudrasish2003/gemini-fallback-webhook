from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import requests
import re

app = FastAPI()

GEMINI_API_KEY = "AIzaSyDD8QW1BggDVVMLteDygHCHrD6Ff9Dy0e8"
GEMINI_MODEL = "gemini-2.0-flash"

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

    reply = ""
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

    # Reset form parameters of the current page
    form_params = body.get("pageInfo", {}).get("formInfo", {}).get("parameterInfo", [])
    reset_params = {}
    for param in form_params:
        param_id = param.get("displayName")
        if param_id:
            reset_params[param_id] = None

    # Final response with reset form parameters and GEMINI_FULLBACK tag
    response_data = {
        "fulfillment_response": {
            "messages": [{"text": {"text": [reply]}}],
            "tag": "GEMINI_FULLBACK"
        },
        "session_info": {
            "parameters": {
                **reset_params,
                "last_response": reply
            }
        }
    }

    return JSONResponse(content=response_data)

@app.post("/webhook")
async def webhook(request: Request):
    body = await request.json()
    return await handle_webhook_logic(body)

@app.post("/{full_path:path}")
async def catch_all_post(full_path: str, request: Request):
    body = await request.json()
    return await handle_webhook_logic(body)
