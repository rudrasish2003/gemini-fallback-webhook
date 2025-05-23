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
    import re

    session_params = body.get("sessionInfo", {}).get("parameters", {})
    
    # Normalize input
    user_input = re.sub(r"\s+", " ", body.get("text", "").strip().lower())
    if not user_input:
        user_input = session_params.get("fallback-input", "Hello")

    # Junk Gemini auto prompts from voice/assistant interfaces
    junk_inputs = [
        "okay, i'm ready! what do you need me to explain? just give me the topic.",
        "okay, i'm ready. ask me a question and i'll give you a concise, helpful answer in 30-40 words.",
        "go ahead, i'm listening.",
        "what would you like to know?"
    ]

    # If input matches known junk or is too short, replace it with a valid fallback
    if user_input in junk_inputs or len(user_input.strip()) < 6:
        print("🛑 Junk voice input detected. Overriding with fallback query.")
        user_input = "what is fedex"

    full_page_path = body.get("pageInfo", {}).get("currentPage", "")
    current_page_id = full_page_path.split("/")[-1] if full_page_path else "Unknown"

    print("🔤 Final cleaned user input:", repr(user_input))

    # Build natural Gemini prompt
    prompt = f"{user_input}\n\nExplain clearly in 30–40 words. No formatting. Be concise and helpful."

    gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": prompt}]
            }
        ]
    }

    print("📤 Sending prompt to Gemini:", prompt)

    try:
        response = requests.post(gemini_url, json=payload)
        response.raise_for_status()
        gemini_json = response.json()
        print("📩 Gemini raw response:", gemini_json)

        candidates = gemini_json.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            if parts and "text" in parts[0]:
                gemini_raw = parts[0]["text"]
            else:
                gemini_raw = ""
        else:
            gemini_raw = ""

        if not gemini_raw:
            raise ValueError("Gemini returned empty response")

        # Clean output
        text = re.sub(r"[*_~`]", "", gemini_raw)
        text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
        words = text.strip().split()
        reply = text if len(words) < 30 else " ".join(words[:40])

    except Exception as e:
        print("❌ Gemini API error:", str(e))
        reply = "Sorry, I couldn't find an answer."

    # Reset form parameters to re-ask
    form_params = body.get("pageInfo", {}).get("formInfo", {}).get("parameterInfo", [])
    reset_params = {}
    for param in form_params:
        param_id = param.get("displayName")
        if param_id:
            reset_params[param_id] = None

    # Final response to Dialogflow
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
