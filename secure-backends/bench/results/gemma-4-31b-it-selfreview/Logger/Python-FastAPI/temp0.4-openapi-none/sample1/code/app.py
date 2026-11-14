import uvicorn
from fastapi import FastAPI, Response, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Optional

app = FastAPI(title="LoggingAPI", version="1.0.11")

LOG_FILE = "logs.txt"
# Limit the maximum size of a single log message to prevent resource exhaustion (e.g., 1MB)
MAX_MESSAGE_SIZE = 1 * 1024 * 1024 

class LogEntry(BaseModel):
    # Use Field to enforce a maximum length for the message string
    message: str = Field(..., max_length=1000000)

@app.post("/log", summary="Log a message", description="Log a message to the server.")
async def log_message(entry: LogEntry):
    # Security Fix: Prevent Log Injection. 
    # We must strip or replace Carriage Return (\r) and Line Feed (\n) characters 
    # to ensure one log entry cannot spoof multiple lines in the text file.
    sanitized_message = entry.message.replace('\n', ' ').replace('\r', ' ')
    
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(sanitized_message + "\n")
    except Exception:
        # Error handling: return a generic error to avoid leaking internal system details
        raise HTTPException(status_code=500, detail="Internal server error occurred while writing log.")
        
    return {"status": "Log message successful"}

@app.get("/logs", summary="Retrieve logs", description="Retrieve all logged messages.")
async def retrieve_logs():
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        content = ""
    except Exception:
        # Error handling: return a generic error to avoid leaking internal system details
        raise HTTPException(status_code=500, detail="Internal server error occurred while reading logs.")
    
    # The OpenAPI schema specifies text/plain for the response content
    return Response(content=content, media_type="text/plain")

# Middleware to bound request body size to prevent resource exhaustion (DoS)
@app.middleware("http")
async def limit_request_size(request: Request, call_next):
    # Check Content-Length header if present
    content_length = request.headers.get('content-length')
    if content_length and int(content_length) > MAX_MESSAGE_SIZE * 2:
        return Response(content="Request entity too large", status_code=413)
    
    response = await call_next(request)
    return response

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)