from fastapi import FastAPI, Request
from pydantic import BaseModel
import os
from datetime import datetime

app = FastAPI()

# Ensure transcript folder exists
os.makedirs("transcripts", exist_ok=True)

class TranscriptPayload(BaseModel):
    sessionId: str
    speaker: str
    transcript: str
    timestamp: str

@app.post("/ultravox-webhook")
async def receive_transcript(payload: TranscriptPayload):
    file_path = f"transcripts/{payload.sessionId}.txt"

    line = f"[{payload.timestamp}] {payload.speaker}: {payload.transcript}\n"
    with open(file_path, "a", encoding="utf-8") as f:
        f.write(line)

    return {"status": "received"}
