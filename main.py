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

        if session_id not in sessions:
            sessions[session_id] = {"dialog": [], "qa": []}

        # Track conversation
        if transcript:
            sessions[session_id]["dialog"].append({
                "timestamp": timestamp,
                "speaker": speaker,
                "text": transcript
            })

            if "?" in transcript.lower() and speaker.lower() == "agent":
                sessions[session_id]["qa"].append({"question": transcript, "answer": ""})
            elif speaker.lower() != "agent" and sessions[session_id]["qa"]:
                if sessions[session_id]["qa"][-1]["answer"] == "":
                    sessions[session_id]["qa"][-1]["answer"] = transcript

        # On call end, extract and parse
        if data.get("event") == "call.ended" and call_data:
            short_summary = call_data.get("shortSummary", "")
            full_summary = call_data.get("summary", "")

            print(f"\n✅ Call Ended — ID: {session_id}")
            print(f"📋 Short Summary:\n{short_summary}")
            print(f"📝 Full Summary:\n{full_summary}")

            parsed_info = {}

            patterns = {
                "interested_in_role": r"(expressed interest.*?position|not interested)",
                "fedex_experience": r"(former FedEx driver|worked for FedEx[^.,]*)",
                "fedex_id": r"FedEx ID.*?[\"']?([A-Za-z0-9\-]+)[\"']?",
                "fedex_last_working_day": r"last working day (?:was|is|in)\s+([\w\s\d]+)",
                "reason_for_leaving": r"(left .*? to .*?)[.,]",
                "dot_card": r"(has|have|possess|with)[^.,;]*DOT Medical Card",
                "transportation": r"(reliable transportation|no reliable transportation)",
                "availability": r"(available to (?:start|work)[^.,;]*)",
                "age": r"(\d{2}-year-old|over 21|under 21|above 21)",
                "background_check": r"(pass[^.,;]*background check[^.,;]*|drug test[^.,;]*|physical[^.,;]*)"
            }

            for key, pattern in patterns.items():
                match = re.search(pattern, full_summary, re.IGNORECASE)
                if match:
                    if key == "fedex_id":
                        parsed_info[key] = match.group(1).strip()
                    else:
                        parsed_info[key] = match.group(0).strip()
                else:
                    parsed_info[key] = "Not mentioned"

            print("\n📦 Parsed Candidate Information:")
            for k, v in parsed_info.items():
                print(f"{k}: {v}")

            print("\n📚 Candidate Q&A:")
            for pair in sessions[session_id]["qa"]:
                print(f"Q: {pair['question']}\nA: {pair['answer']}\n")

            print("📜 Full Transcript:")
            for line in sessions[session_id]["dialog"]:
                print(f"[{line['timestamp']}] {line['speaker']}: {line['text']}")

            sessions.pop(session_id, None)

        return {"status": "received"}

    except Exception as e:
        print("❌ Error processing webhook:", str(e))
        return {"status": "error", "message": str(e)}
