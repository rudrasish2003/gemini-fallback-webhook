import os
import json
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import httpx
from bs4 import BeautifulSoup

app = FastAPI()

# Constants
GEMINI_MODEL = "gemini-2.0-flash"
GEMINI_API_KEY =   "AIzaSyDD8QW1BggDVVMLteDygHCHrD6Ff9Dy0e8"

# Fixed JD link
JD_LINK = "https://funnl.team/flatirontruckinginc/noncdll20/Jobdetails"  # 🔁 replace with actual JD URL

# Extract user input
def extract_user_input(body: dict) -> str:
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

# Fetch JD content
async def fetch_jd_text() -> str:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(JD_LINK, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            return soup.get_text(separator="\n", strip=True)
    except Exception as e:
        print(f"❌ Failed to fetch JD: {e}")
        return ""

# Query Gemini
async def query_gemini(question: str, jd_text: str) -> str:
    prompt = f"""
You are an HR representative answering candidate questions about a job role.

ONLY use the information from the job description below. Do not guess or add extra details.

If the question cannot be answered using the JD, respond with:
"I’m not sure about that. Let me get someone to help you."

Avoid using phrases like "Based on the JD" or "According to the job description".

--- JOB DESCRIPTION START ---
{jd_text}
--- JOB DESCRIPTION END ---

Candidate Question:
{question}

Answer:
""".strip()

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}]
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers={"Content-Type": "application/json"}, json=payload)
        response.raise_for_status()
        data = response.json()

        candidates = data.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            return " ".join(p.get("text", "") for p in parts if "text" in p).strip()

        return "I’m not sure about that. Let me get someone to help you."

# Dialogflow-compatible webhook
@app.post("/webhook")
async def webhook(request: Request):
    body = await request.json()
    print("📥 Webhook body:", json.dumps(body, indent=2))

    question = extract_user_input(body)
    jd_text = await fetch_jd_text()

    if not jd_text:
        return JSONResponse(content={
            "fulfillment_response": {
                "messages": [{"text": {"text": ["Sorry, I couldn’t access the job description. Please try again later."]}}]
            }
        })

    try:
        answer = await query_gemini(question, jd_text)
        print("📩 Gemini response:", answer)
    except Exception as e:
        print("❌ Gemini error:", str(e))
        answer = "Sorry, I'm having trouble right now."

    return JSONResponse(content={
        "fulfillment_response": {
            "messages": [{"text": {"text": [answer]}}]
        }
    })
