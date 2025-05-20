from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import requests

app = FastAPI()

GEMINI_API_KEY = "AIzaSyDD8QW1BggDVVMLteDygHCHrD6Ff9Dy0e8"
GEMINI_MODEL = "gemini-2.0-flash"

@app.post("/webhook")
async def webhook(request: Request):
    body = await request.json()
    print("Received from Dialogflow CX:", body)

    # Extract text from user input (no-match fallback or general input)
    user_input = body.get("text")
    if not user_input:
        # Fallback: Try from sessionInfo parameters if text missing
        user_input = body.get("sessionInfo", {}).get("parameters", {}).get("text", "Hello")

    # Prepare Gemini API request
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
        reply = response.json()["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        print("Gemini API error:", str(e))
        reply = "Sorry, I couldn't find an answer."

    # Build response in Dialogflow CX-compatible format
    return JSONResponse(content={
        "fulfillment_response": {
            "messages": [
                {
                    "text": {
                        "text": [reply]
                    }
                }
            ]
        },
        "session_info": {
            "parameters": {
                "last_response": reply
            }
        },
        "target_page": "",  # Optional: leave blank to stay on the same page
        "target_flow": "",  # Optional
        "tag": body.get("fulfillmentInfo", {}).get("tag", "")
    })
