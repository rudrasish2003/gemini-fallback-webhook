from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import requests

app = FastAPI()

GEMINI_API_KEY = "AIzaSyDD8QW1BggDVVMLteDygHCHrD6Ff9Dy0e8"
GEMINI_MODEL = "gemini-2.0-flash"

# Dialogflow CX agent details (Confirm flow_id and page name before use)
PROJECT_ID = "intervue-ucxu"
LOCATION_ID = "us-central1"
AGENT_ID = "503d60e1-4e8e-420a-b0ef-db6d0e281464"
FLOW_ID = "00000000-0000-0000-0000-000000000000"  # <--- Update this
CONFIRM_PAGE_ID = "ConfirmPage"  # <--- Update if your ConfirmPage has a different name

@app.post("/webhook")
async def webhook(request: Request):
    body = await request.json()
    print("✅ Received from Dialogflow CX:", body)

    tag = body.get("fulfillmentInfo", {}).get("tag", "")
    user_input = body.get("text")

    if not user_input:
        user_input = body.get("sessionInfo", {}).get("parameters", {}).get("fallback-input", "Hello")

    # Get current page path (full resource name)
    full_page_path = body.get("pageInfo", {}).get("currentPage", "")
    current_page = full_page_path.split("/")[-1] if full_page_path else "Unknown"

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
        print("❌ Gemini API error:", str(e))
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
        "session_info": {
            "parameters": {
                "last_response": reply,
                "last_page": current_page
            }
        },
        "target_page": f"projects/{PROJECT_ID}/locations/{LOCATION_ID}/agents/{AGENT_ID}/flows/{FLOW_ID}/pages/{CONFIRM_PAGE_ID}"
    })
