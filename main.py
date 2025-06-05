from fastapi import FastAPI, Request
import os
from datetime import datetime

app = FastAPI()

# Ensure transcript folder exists
os.makedirs("transcripts", exist_ok=True)

@app.post("/ultravox-webhook")
async def receive_transcript(request: Request):
    try:
        # Try to parse the incoming JSON body
        data = await request.json()
        print("📥 Received JSON Payload:", data)

        # Extract values with defaults in case fields are missing
        session_id = data.get("sessionId") or data.get("session_id", "unknown_session")
        speaker = data.get("speaker") or data.get("agent", "unknown_speaker")
        transcript = data.get("transcript") or data.get("text", "")
        timestamp = data.get("timestamp") or data.get("time", datetime.utcnow().isoformat())

        # Compose and write to file
        file_path = f"transcripts/{session_id}.txt"
        line = f"[{timestamp}] {speaker}: {transcript}\n"

        with open(file_path, "a", encoding="utf-8") as f:
            f.write(line)

        return {"status": "received"}

    except Exception as e:
        print("❌ Error processing webhook:", str(e))
        return {"status": "error", "message": str(e)}
