from fastapi import FastAPI, Request
from datetime import datetime
import re
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import os

app = FastAPI()
sessions = {}

# ✅ Regex for email detection
EMAIL_REGEX = re.compile(r"[\w\.-]+@[\w\.-]+\.\w+")

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

        # Track dialogue
        if transcript:
            sessions[session_id]["dialog"].append({
                "timestamp": timestamp,
                "speaker": speaker,
                "text": transcript
            })

            # Q&A tracker
            if "?" in transcript.lower() and speaker.lower() == "agent":
                sessions[session_id]["qa"].append({"question": transcript, "answer": ""})
            elif speaker.lower() != "agent" and sessions[session_id]["qa"]:
                if sessions[session_id]["qa"][-1]["answer"] == "":
                    sessions[session_id]["qa"][-1]["answer"] = transcript

            # ✅ Real-time email detection and send
            if not sessions[session_id]["email_sent"]:
                email_match = EMAIL_REGEX.search(transcript)
                if email_match:
                    email = email_match.group(0)
                    if send_verification_email(email):
                        sessions[session_id]["email_sent"] = True
                        print(f"📨 Sent verification email to: {email}")

        # ✅ On call end: log everything and cleanup
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

            # ✅ cleanup
            sessions.pop(session_id, None)

        return {"status": "received"}

    except Exception as e:
        print("❌ Error processing webhook:", str(e))
        return {"status": "error", "message": str(e)}
