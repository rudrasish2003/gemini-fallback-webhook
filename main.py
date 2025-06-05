from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
import os
from datetime import datetime

app = FastAPI()

# Create a persistent folder on the server (works on Render with a persistent disk)
TRANSCRIPT_DIR = "transcripts"
os.makedirs(TRANSCRIPT_DIR, exist_ok=True)

@app.post("/ultravox-webhook")
async def receive_transcript(request: Request):
    try:
        data = await request.json()
        print("📥 Received JSON Payload:", data)

        # Extract fields from payload
        session_id = data.get("sessionId") or data.get("session_id") or "unknown_session"
        speaker = data.get("speaker") or data.get("agent") or "unknown_speaker"
        transcript = data.get("transcript") or data.get("text") or ""
        timestamp = data.get("timestamp") or data.get("time") or datetime.utcnow().isoformat()

        # Write transcript to file
        file_path = os.path.join(TRANSCRIPT_DIR, f"{session_id}.txt")
        line = f"[{timestamp}] {speaker}: {transcript}\n"

        with open(file_path, "a", encoding="utf-8") as f:
            f.write(line)

        return {"status": "received"}

    except Exception as e:
        print("❌ Error processing webhook:", str(e))
        return {"status": "error", "message": str(e)}

@app.get("/download-transcript/{session_id}")
async def download_transcript(session_id: str):
    file_path = os.path.join(TRANSCRIPT_DIR, f"{session_id}.txt")
    if os.path.exists(file_path):
        return FileResponse(path=file_path, filename=f"{session_id}.txt", media_type='text/plain')
    return {"error": "Transcript not found"}
