from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
import os
from datetime import datetime

app = FastAPI()

# === Directory setup (works on Render with persistent disk if enabled) ===
TRANSCRIPT_DIR = "transcripts"
os.makedirs(TRANSCRIPT_DIR, exist_ok=True)

@app.post("/ultravox-webhook")
async def receive_transcript(request: Request):
    try:
        data = await request.json()
        print("📥 Received JSON Payload:", data)

        # === Handle real-time transcript chunks ===
        session_id = data.get("sessionId") or data.get("session_id") or "unknown_session"
        speaker = data.get("speaker") or data.get("agent") or "unknown_speaker"
        transcript = data.get("transcript") or data.get("text") or ""
        timestamp = data.get("timestamp") or data.get("time") or datetime.utcnow().isoformat()

        if transcript:
            line = f"[{timestamp}] {speaker}: {transcript}\n"
            file_path = os.path.join(TRANSCRIPT_DIR, f"{session_id}.txt")

            with open(file_path, "a", encoding="utf-8") as f:
                f.write(line)

            print(line.strip())

        # === Handle full call summary on call.ended ===
        if data.get("event") == "call.ended" and "call" in data:
            call = data["call"]
            call_id = call.get("callId", session_id)
            short_summary = call.get("shortSummary", "")
            full_summary = call.get("summary", "")

            summary_path = os.path.join(TRANSCRIPT_DIR, f"{call_id}_summary.txt")
            with open(summary_path, "w", encoding="utf-8") as f:
                f.write(f"📋 Short Summary:\n{short_summary}\n\n📝 Full Summary:\n{full_summary}\n")

            print("✅ Summary saved for call:", call_id)
            print("📋", short_summary)
            print("📝", full_summary)

        return {"status": "received"}

    except Exception as e:
        print("❌ Error processing webhook:", str(e))
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

@app.get("/download-transcript/{session_id}")
async def download_transcript(session_id: str):
    file_path = os.path.join(TRANSCRIPT_DIR, f"{session_id}.txt")
    if os.path.exists(file_path):
        return FileResponse(path=file_path, filename=f"{session_id}.txt", media_type='text/plain')
    return JSONResponse(status_code=404, content={"error": "Transcript not found"})

@app.get("/download-summary/{call_id}")
async def download_summary(call_id: str):
    file_path = os.path.join(TRANSCRIPT_DIR, f"{call_id}_summary.txt")
    if os.path.exists(file_path):
        return FileResponse(path=file_path, filename=f"{call_id}_summary.txt", media_type='text/plain')
    return JSONResponse(status_code=404, content={"error": "Summary not found"})
