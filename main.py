import os
import json
import asyncio
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import httpx

app = FastAPI()

GEMINI_API_URL = "https://gemini.api/endpoint"  # replace with your Gemini API URL
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")    # set your API key in environment variables

def extract_user_input(body: dict) -> str:
    # Priority: transcript (voice) > text (typed) > session params > default "hello"
    transcript = body.get("transcript", "").strip()
    if transcript:
        print("🎤 Using voice transcript as input:", repr(transcript))
        return transcript.lower()

    text = body.get("text", "").strip()
    if text:
        print("⌨️ Using text input:", repr(text))
        return text.lower()

    session_params = body.get("sessionInfo", {}).get("parameters", {})
    fallback_input = session_params.get("user_input", "").strip()
    if fallback_input:
        print("🔄 Using session parameter user_input:", repr(fallback_input))
        return fallback_input.lower()

    print("⚠️ No user input found; defaulting to 'hello'")
    return "hello"

async def query_gemini(prompt: str) -> str:
    headers = {
        "Authorization": f"Bearer {GEMINI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "prompt": prompt,
        # add other required Gemini API parameters here
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(GEMINI_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

        # Extract the text answer from Gemini's response structure
        candidates = data.get("candidates", [])
        if candidates and "content" in candidates[0]:
            parts = candidates[0]["content"].get("parts", [])
            if parts:
                return parts[0].get("text", "").strip()

        return "Sorry, I couldn't get a response from Gemini."

@app.post("/webhook")
async def webhook(request: Request):
    body = await request.json()
    print("📥 Full webhook request body:", json.dumps(body, indent=2))

    user_input = extract_user_input(body)
    print("✅ Extracted user input:", repr(user_input))

    prompt = f"{user_input}\n\nAnswer in 30 to 40 words. Keep it clear and concise."
    print("📤 Prompt sent to Gemini:", prompt)

    try:
        gemini_response = await query_gemini(prompt)
        print("📩 Gemini response:", gemini_response)
    except Exception as e:
        print("❌ Error querying Gemini:", e)
        gemini_response = "Sorry, I'm having trouble right now."

    # Build the response JSON expected by Dialogflow CX webhook
    fulfillment_response = {
        "fulfillment_response": {
            "messages": [
                {
                    "text": {
                        "text": [gemini_response]
                    }
                }
            ]
        }
    }

    return JSONResponse(content=fulfillment_response)
