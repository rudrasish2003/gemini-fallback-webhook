from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import requests

app = FastAPI()
GEMINI_API_KEY = "AIzaSyDD8QW1BggDVVMLteDygHCHrD6Ff9Dy0e8"
GEMINI_MODEL = "gemini-2.0-flash"

@app.post("/webhook")
async def webhook(request: Request):
    body = await request.json()
    print("Request from Dialogflow CX:", body)

    # Get user input (Dialogflow CX sends 'text' field)
    text = body.get("text", "Hello")

    gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": text}]
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
        # Include tag only if Dialogflow CX is matching against it
         "tag": "GEMINI_FALLBACK"
    })
