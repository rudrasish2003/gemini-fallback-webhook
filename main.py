from fastapi import FastAPI, Request
from datetime import datetime
import re
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from email_validator import validate_email, EmailNotValidError
import os

app = FastAPI()
sessions = {}

# ✅ Normalize and extract email from text like: "john dot doe at gmail dot com"
def normalize_and_extract_email(text: str):
    cleaned = (
        text.lower()
        .replace(" at ", "@")
        .replace(" dot ", ".")
        .replace(" underscore ", "_")
        .replace(" dash ", "-")
        .replace(" ", "")
    )
    match = re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", cleaned)
    if match:
        try:
            valid = validate_email(match.group(0))
            return valid.email
        except EmailNotValidError:
            return None
    return None

# ✅ SendGrid email sender
def send_verification_email(to_email):
    message = Mail(
        from_email=os.getenv("SENDER_EMAIL"),
        to_emails=to_email,
        subject="FedEx Job Verification Email",
        html_content="""
        <p>Hello,</p>
        <p>Thank you for your interest in the Non CDL/L20 role at FedEx.</p>
        <p>This is a verification email confirming your contact details.</p>
        <p>Our team will follow up with the next steps shortly.</p>
        <br>
        <p>– RecruitAI (FedEx)</p>
        """)
    try:
        sg = SendGridAPIClient(os.getenv("SENDGRID_API_KEY"))
        response = sg.send(message)
        print(f"✅ Email sent to {to_email} (Status: {response.status_code})")
        return True
    except Exception as e:
        print(f"❌ SendGrid error: {str(e)}")
        return False

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
            sessions[session_id] = {"dialog": [], "qa": [], "email_sent": False}

        # Track conversation
        if transcript:
            sessions[session_id]["dialog"].append({
                "timestamp": timestamp,
                "speaker": speaker,
                "text": transcript
            })

            # Q&A tracking
            if "?" in transcript.lower() and speaker.lower() == "agent":
                sessions[session_id]["qa"].append({"question": transcript, "answer": ""})
            elif speaker.lower() != "agent" and sessions[session_id]["qa"]:
                if sessions[session_id]["qa"][-1]["answer"] == "":
                    sessions[session_id]["qa"][-1]["answer"] = transcript

            # ✅ Real-time email spell check and sending
            if not sessions[session_id]["email_sent"] and speaker.lower() != "agent":
                normalized_email = normalize_and_extract_email(transcript)
                if normalized_email and send_verification_email(normalized_email):
                    sessions[session_id]["email_sent"] = True
                    print(f"📨 Sent verification email to: {normalized_email}")

        # ✅ On call end
        if data.get("event") == "call.ended" and call_data:
            short_summary = call_data.get("shortSummary", "")
            full_summary = call_data.get("summary", "")

            print(f"\n✅ Call Ended — ID: {session_id}")
            print(f"📋 Short Summary:\n{short_summary}")
            print(f"📝 Full Summary:\n{full_summary}")

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
