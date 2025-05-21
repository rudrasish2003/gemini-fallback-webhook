from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import requests
import re

app = FastAPI()

# Gemini setup
GEMINI_API_KEY = "AIzaSyDD8QW1BggDVVMLteDygHCHrD6Ff9Dy0e8"
GEMINI_MODEL = "gemini-2.0-flash"

# Dialogflow CX agent details
PROJECT_ID = "intervue-ucxu"
LOCATION_ID = "us-central1"
AGENT_ID = "503d60e1-4e8e-420a-b0ef-db6d0e281464"
FLOW_ID = "00000000-0000-0000-0000-000000000000"
CONFIRM_PAGE_ID = "c2bd0e45-a3c4-4ec4-b54b-013e61b41207"

def clean_and_trim_text(text: str) -> str:
    # Remove markdown formatting
    text = re.sub(r"[*_~`]", "", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    words = text.strip().split()
    return text if len(words) < 30 else " ".join(words[:40])

@app.post("/webhook")
async def webhook(request: Request):
    body = await request.json()
    print("✅ Received request:", body)

    session_params = body.get("sessionInfo", {}).get("parameters", {})
    tag = body.get("fulfillmentInfo", {}).get("tag", "")
    user_input = body.get("text", "").lower().strip()

    full_page_path = body.get("pageInfo", {}).get("currentPage", "")
    current_page_id = full_page_path.split("/")[-1] if full_page_path else "Unknown"
    last_page = session_params.get("last_page")
    update_last_page = full_page_path if current_page_id != CONFIRM_PAGE_ID else last_page

    reply = ""
    target_page = None

    print("📄 Current Page ID:", current_page_id)
    print("📌 Full Page Path:", full_page_path)
    print("📦 Last Stored Page:", last_page)

    # ✅ If on ConfirmPage: handle 'yes'/'no'
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

    # ✅ Else: use Gemini and prompt again
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
        except Exception as e:
            print("❌ Gemini API Error:", str(e))
            cleaned = "Sorry, I couldn't find an answer."

        # Append the fallback question to clarify again
        fallback_prompt = "Could you please answer yes or no? Do you have a DOT Medical Card?"
        reply = f"{cleaned} {fallback_prompt}"

        # ❗ Do NOT redirect – stay on same page to avoid loop
        target_page = None

    # ✅ Build final response
    response_data = {
        "fulfillment_response": {
            "messages": [{"text": {"text": [reply]}}]
        },
        "session_info": {
            "parameters": {
                "last_response": reply,
                "last_page": update_last_page
            }
        }
    }

    if target_page:
        response_data["target_page"] = target_page
        print("🎯 Redirecting to target_page:", target_page)

    return JSONResponse(content=response_data)
