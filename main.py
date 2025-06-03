import os
import json
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import httpx
from bs4 import BeautifulSoup

app = FastAPI()

# Constants
GEMINI_MODEL = "gemini-2.0-flash"
GEMINI_API_KEY = "AIzaSyDD8QW1BggDVVMLteDygHCHrD6Ff9Dy0e8"
JD_LINK = "https://funnl.team/flatirontruckinginc/noncdll20/Jobdetails"

def extract_user_input(body: dict) -> str:
    transcript = body.get("transcript", "").strip()
    if transcript:
        return transcript.lower()
    text = body.get("text", "").strip()
    if text:
        return text.lower()
    session_params = body.get("sessionInfo", {}).get("parameters", {})
    return session_params.get("user_input", "hello").lower()

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

async def query_gemini_with_jd(question: str, jd_text: str) -> str:
    prompt = f"""
You are an HR assistant. ONLY answer using this job description. Do not add extra information.

If not answerable, reply:
"I’m not sure about that. Let me get someone to help you."

Avoid phrases like "Based on the JD".

--- JOB DESCRIPTION ---
{jd_text}
--- END JD ---

Candidate Question:
{question}

Answer:
"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt.strip()}]}]
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers={"Content-Type": "application/json"}, json=payload)
        response.raise_for_status()
        parts = response.json().get("candidates", [])[0].get("content", {}).get("parts", [])
        return " ".join(p.get("text", "") for p in parts).strip()

async def query_global_gemini(question: str) -> str:
    prompt = f"""
You are a helpful assistant.

Answer the question below in 10 to 20 words. Be clear, concise, and skip greetings.

Question: {question}
Answer:
"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt.strip()}]}]
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers={"Content-Type": "application/json"}, json=payload)
        response.raise_for_status()
        parts = response.json().get("candidates", [])[0].get("content", {}).get("parts", [])
        return " ".join(p.get("text", "") for p in parts).strip()

@app.post("/webhook")
async def webhook(request: Request):
    body = await request.json()
    question = extract_user_input(body)
    jd_text = await fetch_jd_text()

    if not jd_text:
        return JSONResponse(content={
            "fulfillment_response": {
                "messages": [{"text": {"text": ["Sorry, the job description couldn’t be accessed."]}}]
            }
        })

    try:
        jd_answer = await query_gemini_with_jd(question, jd_text)
        if "let me get someone to help you" in jd_answer.lower():
            print("🔁 JD insufficient. Searching globally...")
            final_answer = await query_global_gemini(question)
        else:
            final_answer = jd_answer
    except Exception as e:
        print("❌ Gemini error:", str(e))
        final_answer = "Sorry, I'm having trouble right now."

    return JSONResponse(content={
        "fulfillment_response": {
            "messages": [{"text": {"text": [final_answer]}}]
        }
    })
