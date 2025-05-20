from fastapi import FastAPI, Request
import requests, os

app = FastAPI()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = "AIzaSyDD8QW1BggDVVMLteDygHCHrD6Ff9Dy0e8"

@app.post("/webhook")
async def webhook(request: Request):
    body = await request.json()
    try:
        text = body['text'] if 'text' in body else body['queryResult']['queryText']
    except:
        text = "Hello"

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
    except:
        reply = "Sorry, I couldn't find an answer."

    return {
        "fulfillment_response": {
            "messages": [
                {
                    "text": {
                        "text": [reply]
                    }
                }
            ]
        }
    }
