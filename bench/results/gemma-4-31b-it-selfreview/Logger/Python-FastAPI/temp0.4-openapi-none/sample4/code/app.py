import uvicorn
from fastapi import FastAPI, Response, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Optional

app = FastAPI(title="LoggingAPI", version="1.0.11")

LOG_FILE = "logs.txt"
# Limit request body size to prevent resource exhaustion (e.g., 1MB)
MAX_CONTENT_LENGTH = 1 * 1024 * 1024 

class LogMessage(BaseModel):
    # Bound the length of the message to prevent resource exhaustion/DoS
    message: str = Field(..., max_length=10000)

@app.post("/log", summary="Log a message", description="Log a message to the server.")
async def log_message(request: Request, log: LogMessage):
    # Check for resource exhaustion: ensure the raw body size is within limits
    # Note: FastAPI/Pydantic handles the parsing, but we check the content length header
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_CONTENT_LENGTH:
        raise HTTPException(status_code=413, detail="Request entity Too Large")

    # Security Fix: Prevent Log Injection (CRLF injection)
    # Reject or strip CR/LF characters to prevent attackers from forging log entries
    # or manipulating log files.
    sanitized_message = log.message.replace('\r', '').replace('\n', ' ')

    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(sanitized_message + "\n")
    except Exception:
        # Error handling: catch exceptions and return a generic error to avoid leaking internal details
        raise HTTPException(status_code=500, detail="Internal server error")
        
    return {"status": "Log message successful"}

@app.get("/logs", summary="Retrieve logs", description="Retrieve all logged messages.")
async def retrieve_logs():
    try:
        # Resource exhaustion: limit the amount of data read from the file
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            content = f.read(MAX_CONTENT_LENGTH)
    except FileNotFoundError:
        content = ""
    except Exception:
        # Error handling: prevent leaking stack traces
        raise HTTPException(status_code=500, detail="Internal server error")
    
    return Response(content=content, media_type="text/plain")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)