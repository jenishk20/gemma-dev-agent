import uvicorn
from fastapi import FastAPI, Response, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Optional

app = FastAPI(title="LoggingAPI", version="1.0.11")

LOG_FILE = "logs.txt"
# Limit request body size to prevent resource exhaustion (e.g., 1MB)
MAX_CONTENT_LENGTH = 1024 * 1024 

class LogRequest(BaseModel):
    # Bound the input size to prevent resource exhaustion
    message: str = Field(..., max_length=10000)

@app.post("/log", summary="Log a message", description="Log a message to the server.")
async def log_message(request: LogRequest):
    # Security Fix: Prevent Log Injection. 
    # Reject or strip CR/LF characters to prevent attackers from forging log entries 
    # or manipulating log files.
    if "\n" in request.message or "\r" in request.message:
        # Since the spec doesn't define a specific error for bad input, 
        # we use a standard 400 Bad Request to reject malicious input.
        raise HTTPException(status_code=400, detail="Message contains invalid characters (CR/LF)")

    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(request.message + "\n")
    except Exception:
        # Error handling: return a generic error to avoid leaking internal details
        raise HTTPException(status_code=500, detail="Internal server error")
        
    return {"status": "Log message successful"}

@app.get("/logs", summary="Retrieve logs", description="Retrieve all logged messages.")
async def retrieve_logs():
    try:
        # Resource exhaustion: Read the file in a way that doesn't crash the server 
        # if the file grows too large.
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            content = f.read(MAX_CONTENT_LENGTH)
    except FileNotFoundError:
        content = ""
    except Exception:
        # Error handling: return a generic error to avoid leaking internal details
        raise HTTPException(status_code=500, detail="Internal server error")
    
    return Response(content=content, media_type="text/plain")

# Middleware to enforce request size limit globally
@app.middleware("http")
async def limit_request_size(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_CONTENT_LENGTH:
        return Response(content="Request entity too large", status_code=413)
    return await call_next(request)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)