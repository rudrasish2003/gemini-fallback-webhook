from fastapi import FastAPI, Request
import requests

app = FastAPI()

GEMINI_API_KEY = "AIzaSyDD8QW1BggDVVMLteDygHCHrD6Ff9Dy0e8"
GEMINI_MODEL = "gemini-2.0-flash"

@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()

    query_text = data['queryResult']['queryText']
    is_fallback = data['queryResult']['intent'].get('isFallback', False)
    contexts = data['queryResult'].get('outputContexts', [])

    if is_fallback:
        try:
            gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
            gemini_payload = {
                "contents": [
                    {
                        "role": "user",
                        "parts": [{"text": query_text}]
                    }
                ]
            }

            response = requests.post(gemini_url, json=gemini_payload)
            response.raise_for_status()
            gemini_reply = response.json()["candidates"][0]["content"]["parts"][0]["text"]

            return {
                "fulfillmentText": gemini_reply,
                "outputContexts": contexts
            }
        except Exception:
            return {
                "fulfillmentText": "Sorry, I couldn't process your request.",
                "outputContexts": contexts
            }

    return {
        "fulfillmentText": "Non-fallback intent.",
        "outputContexts": contexts
    }
