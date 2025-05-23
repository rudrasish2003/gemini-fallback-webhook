from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import requests
import re

app = FastAPI()

GEMINI_API_KEY = "AIzaSyDD8QW1BggDVVMLteDygHCHrD6Ff9Dy0e8"
GEMINI_MODEL = "gemini-2.0-flash"

def clean_and_trim_text(text: str) -> str:
    text = re.sub(r"[*_~`]", "", text)
    text = re.sub(r"\$\$([^$$]+)\]$$[^)]+$$", r"\1", text)  # Fix regex escape for literal $$
    words = text.strip().split()
    return text if len(words) < 30 else " ".join(words[:40])

async def handle_webhook_logic(body: dict):
    print("📥 Full webhook request body:")
    print(body)  # DEBUG: Inspect entire incoming request

    session_params = body.get("sessionInfo", {}).get("parameters", {})
    query_result = body.get("queryResult", {})
    original_request = body.get("originalDetectIntentRequest", {})

    print("🧾 queryResult:")
    print(query_result)

    print("🧾 originalDetectIntentRequest:")
    print(original_request)

    # Extract user input from multiple possible fields for text and voice input
    user_input = (
        body.get("text") or
        query_result.get("transcript") or
        (query_result.get("interpretations") and
         query_result["interpretations"][0].get("transcript")) or
        query_result.get("text") or
        query_result.get("queryText") or
        (original_request.get("payload", {})
            .get("inputs", [{}])[0]
            .get("rawInputs", [{}])[0]
            .get("query")) or
        session_params.get("user_input") or
        "hello"  # Fallback
    )

    user_input = (user_input or "hello").strip().lower()
    print("✅ Extracted user input:", repr(user_input))

    prompt = f"{user_input}\n\nAnswer in 30 to 40 words. Keep it clear and concise."

    gemini_url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    )
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": prompt}]
            }
        ]
    }

    print("📤 Prompt sent to Gemini:", prompt)

    try:
        response = requests.post(gemini_url, json=payload)
        response.raise_for_status()
        gemini_json = response.json()
        print("📩 Gemini raw response:", gemini_json)

        candidates = gemini_json.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            gemini_raw = " ".join([
                p.get("text", "") for p in parts if isinstance(p, dict) and "text" in p
            ]).strip()
        else:
            gemini_raw = ""

        if not gemini_raw:
            raise ValueError("Gemini returned empty response")

        # Clean and trim Gemini response
        text = re.sub(r"[*_~`]", "", gemini_raw)
        text = re.sub(r"\$\$([^$$]+)\]$$[^)]+$$", r"\1", text)
        words = text.strip().split()
        reply = text if len(words) < 30 else " ".join(words[:40])
        if len(reply) > 400:
            reply = reply[:397] + "..."

    except Exception as e:
        print("❌ Gemini API error:", str(e))
        try:
            print("⚠️ Gemini error response:", response.json())
        except:
            print("⚠️ Gemini response not available.")
        reply = "Sorry, I couldn't find an answer."

    # Reset form parameters
    form_params = body.get("pageInfo", {}).get("formInfo", {}).get("parameterInfo", [])
    reset_params = {}
    for param in form_params:
        param_id = param.get("displayName")
        if param_id:
            reset_params[param_id] = None

    combined_text = f"🔍 You asked: \"{user_input}\"\n🤖 Gemini says: {reply}"
    response_data = {
        "fulfillment_response": {
            "messages": [{
                "text": {
                    "text": [combined_text]
                }
            }],
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
