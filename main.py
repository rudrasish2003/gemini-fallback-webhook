from fastapi import FastAPI, Request
from datetime import datetime
import re

app = FastAPI()

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
            sessions[session_id] = {"dialog": [], "qa": []}

        # Store dialogue
        if transcript:
            sessions[session_id]["dialog"].append({
                "timestamp": timestamp,
                "speaker": speaker,
                "text": transcript
            })

            # Store Q&A
            if "?" in transcript.lower() and speaker.lower() == "agent":
                sessions[session_id]["qa"].append({"question": transcript, "answer": ""})
            elif speaker.lower() != "agent" and sessions[session_id]["qa"]:
                if sessions[session_id]["qa"][-1]["answer"] == "":
                    sessions[session_id]["qa"][-1]["answer"] = transcript

        # Handle end of call
        if data.get("event") == "call.ended" and call_data:
            short_summary = call_data.get("shortSummary", "")
            full_summary = call_data.get("summary", "")

            print(f"\n✅ Call Ended — ID: {session_id}")
            print(f"📋 Short Summary:\n{short_summary}")
            print(f"📝 Full Summary:\n{full_summary}")

            # ⬇️ Parse full summary into structured JSON
            parsed_info = {
                "has_fedex_experience": "fedex" in full_summary.lower(),
                "has_dot_card": bool(re.search(r"(has|possess|with)\s+(a\s+)?(valid\s+)?dot medical card", full_summary.lower())),
                "has_transportation": "transportation" in full_summary.lower() and "no" not in full_summary.lower(),
                "available_to_start": "available to start" in full_summary.lower(),
                "over_21": "over 21" in full_summary.lower() or "above 21" in full_summary.lower(),
                "part_time_or_full_time": "part-time" in full_summary.lower() and "full-time" in full_summary.lower(),
                "drug_test_clearance": "pass a background check" in full_summary.lower() or "drug test" in full_summary.lower()
            }

            print("\n📦 Parsed Info (from summary):")
            for k, v in parsed_info.items():
                print(f"{k}: {v}")

            print("\n📚 Candidate Q&A:")
            for pair in sessions[session_id]["qa"]:
                print(f"Q: {pair['question']}\nA: {pair['answer']}\n")

            print("📜 Full Transcript:")
            for line in sessions[session_id]["dialog"]:
                print(f"[{line['timestamp']}] {line['speaker']}: {line['text']}")

            # Clean memory
            sessions.pop(session_id, None)

        return {"status": "received"}

    except Exception as e:
        print("❌ Error processing webhook:", str(e))
        return {"status": "error", "message": str(e)}
