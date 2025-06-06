from fastapi import FastAPI, Request
from datetime import datetime

app = FastAPI()

# In-memory cache
transcripts = {}

@app.post("/ultravox-webhook")
async def receive_transcript(request: Request):
    try:
        data = await request.json()
        print("📥 Received JSON Payload:", data)

        # Possible IDs
        call_data = data.get("call", {})
        call_id = call_data.get("callId")
        session_id = data.get("sessionId") or data.get("session_id")

        # Prefer call_id, fallback to session_id
        current_id = call_id or session_id or "unknown_session"

        # Handle real-time transcript line
        transcript = data.get("transcript") or data.get("text", "")
        speaker = data.get("speaker") or data.get("agent") or "unknown_speaker"
        timestamp = data.get("timestamp") or data.get("time") or datetime.utcnow().isoformat()

        if transcript:
            line = f"[{timestamp}] {speaker}: {transcript}"
            transcripts.setdefault(current_id, []).append(line)
            print(line)

        # When call ends, move transcript from session_id (if any) to call_id
        if data.get("event") == "call.ended" and call_data:
            print(f"\n✅ Call Ended — ID: {call_id}")

            short_summary = call_data.get("shortSummary", "")
            full_summary = call_data.get("summary", "")

            print(f"📋 Short Summary:\n{short_summary}")
            print(f"📝 Full Summary:\n{full_summary}")

            # Move transcript from session_id to call_id if necessary
            if call_id and session_id and call_id != session_id:
                if session_id in transcripts:
                    transcripts[call_id] = transcripts.get(call_id, []) + transcripts.pop(session_id)

            full_transcript = "\n".join(transcripts.get(call_id, []))
            print(f"\n📜 Full Transcript:\n{full_transcript}\n")

            # Cleanup
            transcripts.pop(call_id, None)

        return {"status": "received"}

    except Exception as e:
        print("❌ Error processing webhook:", str(e))
        return {"status": "error", "message": str(e)}
