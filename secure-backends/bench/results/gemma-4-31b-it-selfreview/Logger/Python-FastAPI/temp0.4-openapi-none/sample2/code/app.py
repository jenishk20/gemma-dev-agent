import uvicorn
from fastapi import FastAPI, Response, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Optional

app = FastAPI(title="LoggingAPI", version="1.0.11")

LOG_FILE = "logs.txt"
# Limit log file size to prevent resource exhaustion (e.g., 10MB)
MAX_LOG_SIZE = 10 * 1024 * 1024 
# Limit request body size to prevent resource exhaustion
MAX_MESSAGE_LENGTH = 10000 

class LogRequest(BaseModel):
    # Bound the input size to prevent resource exhaustion
    message: str = Field(..., max_length=MAX_MESSAGE_LENGTH)

@app.post("/log", summary="Log a message", description="Log a message to the server.")
async def log_message(request: LogRequest):
    try:
        # Security: Prevent Log Injection (CRLF injection)
        # Strip carriage return and line feed characters to ensure one log entry per line
        sanitized_message = request.message.replace('\r', '').replace('\n', '')
        
        # Resource Exhaustion: Check file size before appending
        import os
        if os.path.exists(LOG_FILE) and os.path.getsize(LOG_FILE) > MAX_LOG_SIZE:
            raise HTTPException(status_code=500, detail="Log storage limit exceeded")

        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(sanitized_message + "\n")
        
        return {"status": "Log message successful"}
    except HTTPException:
        raise
    except Exception:
        # Error handling: Return generic error to avoid leaking internal details
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/logs", summary="Retrieve logs", description="Retrieve all logged messages.")
async def retrieve_logs():
    try:
        # Resource Exhaustion: Prevent reading massive files into memory
        import os
        if os.path.exists(LOG_FILE) and os.path.getsize(LOG_FILE) > MAX_LOG_SIZE:
            # In a real scenario, we might paginate, but per spec we return the logs.
            # We cap the read to prevent memory exhaustion.
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                content = f.read(MAX_LOG_SIZE)
        else:
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                content = f.read()
        
        return Response(content=content, media_type="text/plain")
    except FileNotFoundError:
        return Response(content="", media_type="text/plain")
    except Exception:
        # Error handling: Return generic error to avoid leaking internal details
        raise HTTPException(status_code=500, detail="Internal server error")

if __name__ == "__main__":
    # The server is started on 0.0.0.0:5000 as requested
    uvicorn.run(app, host="0.0.0.0", port=5000)