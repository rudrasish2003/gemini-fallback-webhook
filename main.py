import os
import json
import re
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import httpx

app = FastAPI()

# Use model name only
GEMINI_MODEL = "gemini-2.0-flash"  # You can change this to gemini-1.5-pro, gemini-1.5-flash, etc.
GEMINI_API_KEY =  "AIzaSyDD8QW1BggDVVMLteDygHCHrD6Ff9Dy0e8" # fallback key if not set in environment

def extract_user_input(body: dict) -> str:
    # Priority: transcript (voice) > text (typed) > session params > default
    transcript = body.get("transcript", "").strip()
    if transcript:
        print("🎤 Using voice transcript:", repr(transcript))
        return transcript.lower()

    text = body.get("text", "").strip()
    if text:
        print("⌨️ Using text input:", repr(text))
        return text.lower()

    session_params = body.get("sessionInfo", {}).get("parameters", {})
    fallback = session_params.get("user_input", "").strip()
    if fallback:
        print("🧭 Using fallback input:", repr(fallback))
        return fallback.lower()

    print("⚠️ No input found; defaulting to 'hello'")
    return "hello"

async def query_gemini(prompt: str) -> str:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    headers = {
        "Content-Type": "application/json"
    }
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": prompt}]
            }
        ]
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

        candidates = data.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            text_output = " ".join([p.get("text", "") for p in parts if "text" in p])
            return text_output.strip()

        return "Sorry, no response from Gemini."

@app.post("/webhook")
async def webhook(request: Request):
    body = await request.json()
    print("📥 Webhook request body:", json.dumps(body, indent=2))

    user_input = extract_user_input(body)
    print("✅ Final user input:", user_input)

    prompt = f"{user_input}\n\nAnswer in 30 to 40 words. Keep it clear and concise."
    print("📤 Prompt:", prompt)

    try:
        gemini_response = await query_gemini(prompt)
        print("📩 Gemini reply:", gemini_response)
    except Exception as e:
        print("❌ Gemini error:", str(e))
        gemini_response = "Sorry, I'm having trouble right now."

    return JSONResponse(content={
        "fulfillment_response": {
            "messages": [
                {
                    "text": {
                        "text": [gemini_response]
                    }
                }
            ]
        }
    })
