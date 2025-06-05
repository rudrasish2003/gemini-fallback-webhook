from fastapi import FastAPI, Request
from datetime import datetime

app = FastAPI()

@app.post("/ultravox-webhook")
async def receive_transcript(request: Request):
    try:
        data = await request.json()
        print("📥 Received JSON Payload:", data)

        # === Handle real-time transcript lines ===
        session_id = data.get("sessionId") or data.get("session_id") or "unknown_session"
        speaker = data.get("speaker") or data.get("agent") or "unknown_speaker"
        transcript = data.get("transcript") or data.get("text", "")
        timestamp = data.get("timestamp") or data.get("time") or datetime.utcnow().isoformat()

        if transcript:
            print(f"[{timestamp}] ({session_id}) {speaker}: {transcript}")

        # === Handle full call summary on call.ended ===
        if data.get("event") == "call.ended" and "call" in data:
            call = data["call"]
            call_id = call.get("callId", session_id)
            short_summary = call.get("shortSummary", "")
            full_summary = call.get("summary", "")

            print(f"\n✅ Call Ended — ID: {call_id}")
            print(f"📋 Short Summary:\n{short_summary}")
            print(f"📝 Full Summary:\n{full_summary}\n")

        return {"status": "received"}

    except Exception as e:
        print("❌ Error processing webhook:", str(e))
        return {"status": "error", "message": str(e)}
