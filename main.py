from fastapi import FastAPI, Request
from datetime import datetime

app = FastAPI()

# Store transcripts in memory during call
transcripts = {}

@app.post("/ultravox-webhook")
async def receive_transcript(request: Request):
    try:
        data = await request.json()
        print("📥 Received JSON Payload:", data)

        # Determine session/call ID
        call_data = data.get("call", {})
        session_id = (
            data.get("sessionId")
            or data.get("session_id")
            or call_data.get("callId")
            or "unknown_session"
        )

        # Handle real-time transcript line
        transcript = data.get("transcript") or data.get("text", "")
        speaker = data.get("speaker") or data.get("agent") or "unknown_speaker"
        timestamp = data.get("timestamp") or data.get("time") or datetime.utcnow().isoformat()

        if transcript:
            line = f"[{timestamp}] {speaker}: {transcript}"
            transcripts.setdefault(session_id, []).append(line)
            print(line)

        # Handle call.ended event
        if data.get("event") == "call.ended" and call_data:
            call_id = call_data.get("callId", session_id)
            short_summary = call_data.get("shortSummary", "")
            full_summary = call_data.get("summary", "")

            print(f"\n✅ Call Ended — ID: {call_id}")
            print(f"📋 Short Summary:\n{short_summary}")
            print(f"📝 Full Summary:\n{full_summary}")

            full_transcript = "\n".join(transcripts.get(call_id, []))
            print(f"\n📜 Full Transcript:\n{full_transcript}\n")

            # Clean up in-memory cache
            transcripts.pop(call_id, None)

        return {"status": "received"}

    except Exception as e:
        print("❌ Error processing webhook:", str(e))
        return {"status": "error", "message": str(e)}
