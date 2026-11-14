import uvicorn
from fastapi import FastAPI, Response, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Optional

app = FastAPI(title="LoggingAPI", version="1.0.11")

LOG_FILE = "logs.txt"
# Limit the maximum size of a single log message to prevent resource exhaustion (e.g., 1MB)
MAX_MESSAGE_SIZE = 1024 * 1024 

class LogMessage(BaseModel):
    # Use Field to enforce a maximum length for the message to prevent memory exhaustion
    message: str = Field(..., max_length=MAX_MESSAGE_SIZE)

@app.post("/log", summary="Log a message", description="Log a message to the server.")
async def log_message(log_data: LogMessage):
    # Security Fix: Prevent Log Injection.
    # Untrusted input reaching log lines must have CR/LF characters stripped or rejected
    # to prevent attackers from forging log entries or manipulating log files.
    sanitized_message = log_data.message.replace('\r', '').replace('\n', ' ')
    
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(sanitized_message + "\n")
    except Exception:
        # Error handling: Return a generic error without leaking internal stack traces
        raise HTTPException(status_code=500, detail="Internal server error")
        
    return {"status": "Log message successful"}

@app.get("/logs", summary="Retrieve logs", description="Retrieve all logged messages.")
async def retrieve_logs():
    try:
        # Resource exhaustion: In a production environment, we would paginate this.
        # For this simple service, we read the file. 
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        content = ""
    except Exception:
        # Error handling: Return a generic error without leaking internal stack traces
        raise HTTPException(status_code=500, detail="Internal server error")
    
    return Response(content=content, media_type="text/plain")

if __name__ == "__main__":
    # The server is started on 0.0.0.0:5000 as requested.
    uvicorn.run(app, host="0.0.0.0", port=5000)