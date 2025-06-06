from fastapi import FastAPI, Request
from datetime import datetime

app = FastAPI()

# Store session data in memory
sessions = {}

@app.post("/ultravox-webhook")
async def receive_transcript(request: Request):
    try:
        data = await request.json()
        print("📥 Received JSON Payload:", data)

        call_data = data.get("call", {})
        session_id = (
            data.get("sessionId") or
            data.get("session_id") or
            call_data.get("callId") or
            "unknown_session"
        )

        speaker = data.get("speaker") or data.get("agent") or "unknown_speaker"
        transcript = data.get("transcript") or data.get("text", "")
        timestamp = data.get("timestamp") or data.get("time") or datetime.utcnow().isoformat()

        # Initialize session memory
        if session_id not in sessions:
            sessions[session_id] = {
                "dialog": [],
                "qa": []
            }

        # Save dialog line
        if transcript:
            sessions[session_id]["dialog"].append({
                "timestamp": timestamp,
                "speaker": speaker,
                "text": transcript
            })

            # Build Q&A dynamically
            if "?" in transcript and speaker.lower() == "agent":
                sessions[session_id]["qa"].append({"question": transcript, "answer": ""})
            elif speaker.lower() != "agent" and sessions[session_id]["qa"]:
                if sessions[session_id]["qa"][-1]["answer"] == "":
                    sessions[session_id]["qa"][-1]["answer"] = transcript

        # Handle call end
        if data.get("event") == "call.ended" and call_data:
            short_summary = call_data.get("shortSummary", "")
            full_summary = call_data.get("summary", "")

            print(f"\n✅ Call Ended — ID: {session_id}")
            print(f"📋 Short Summary:\n{short_summary}")
            print(f"📝 Full Summary:\n{full_summary}")

            print(f"\n📚 Candidate Q&A:")
            for pair in sessions[session_id]["qa"]:
                print(f"Q: {pair['question']}\nA: {pair['answer']}\n")

            print("📜 Full Transcript:")
            for line in sessions[session_id]["dialog"]:
                print(f"[{line['timestamp']}] {line['speaker']}: {line['text']}")

            # Optional: Clear memory to free up space
            sessions.pop(session_id, None)

        return {"status": "received"}

    except Exception as e:
        print("❌ Error processing webhook:", str(e))
        return {"status": "error", "message": str(e)}
