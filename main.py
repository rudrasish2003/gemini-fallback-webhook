from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import requests
import re

app = FastAPI()

# Gemini configuration
GEMINI_API_KEY = "AIzaSyDD8QW1BggDVVMLteDygHCHrD6Ff9Dy0e8"
GEMINI_MODEL = "gemini-2.0-flash"

# Clean and trim long or markdown-like text
def clean_and_trim_text(text: str) -> str:
    text = re.sub(r"[*_~`]", "", text)
    text = re.sub(r"\$\$([^$]+)\]\$\$[^\)]+\$\$", r"\1", text)
    words = text.strip().split()
    return text if len(words) < 30 else " ".join(words[:40])

# Webhook logic to handle Dialogflow CX input
async def handle_webhook_logic(body: dict):
    print("📥 Raw request body:", body)

    session_params = body.get("sessionInfo", {}).get("parameters", {})
    query_result = body.get("queryResult", {})

    # Extract user input from all possible Dialogflow CX fields
    user_input = (
        body.get("text") or
        query_result.get("transcript") or
        query_result.get("text") or
        query_result.get("queryText") or
        session_params.get("user_input") or
        session_params.get("fallback-input", "Hello")
    ).strip().lower()

    print("🎤 Transcribed Input (transcript):", query_result.get("transcript"))
    print("📜 Input Text (text):", query_result.get("text"))
    print("📖 Query Text:", query_result.get("queryText"))
    print("✅ Final cleaned user input:", repr(user_input))

    # Build prompt for Gemini
    prompt = f"{user_input}\n\nAnswer in 30 to 40 words. Keep it clear and concise."

    gemini_url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:"
        f"generateContent?key={GEMINI_API_KEY}"
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

        # Parse Gemini output
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

        # Clean and trim Gemini output
        text = clean_and_trim_text(gemini_raw)
        if len(text) > 400:
            text = text[:397] + "..."
        reply = text

    except Exception as e:
        print("❌ Gemini API error:", str(e))
        try:
            print("⚠️ Gemini error response:", response.json())
        except:
            print("⚠️ Gemini response not available.")
        reply = "Sorry, I couldn't find an answer."

    # Reset form parameters if available
    form_params = body.get("pageInfo", {}).get("formInfo", {}).get("parameterInfo", [])
    reset_params = {}
    for param in form_params:
        param_id = param.get("displayName")
        if param_id:
            reset_params[param_id] = None

    # Build Dialogflow CX response
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

# Webhook endpoint
@app.post("/webhook")
async def webhook(request: Request):
    body = await request.json()
    return await handle_webhook_logic(body)

# Catch-all endpoint (optional fallback)
@app.post("/{full_path:path}")
async def catch_all_post(full_path: str, request: Request):
    body = await request.json()
    return await handle_webhook_logic(body)
