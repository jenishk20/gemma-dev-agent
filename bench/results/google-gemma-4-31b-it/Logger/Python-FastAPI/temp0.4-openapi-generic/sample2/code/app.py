import uvicorn
from fastapi import FastAPI, Response
from pydantic import BaseModel
import os

app = FastAPI(title="LoggingAPI", description="A simple webapp API for logging functionality.", version="1.0.11")

LOG_FILE = "logs.txt"

class LogEntry(BaseModel):
    message: str

@app.post("/log", summary="Log a message", description="Log a message to the server.")
async def log_message(entry: LogEntry):
    # Sanitize input by removing newline characters to prevent log injection
    # and ensure each log entry stays on one line as per requirements.
    sanitized_message = entry.message.replace('\n', ' ').replace('\r', ' ')
    
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(sanitized_message + "\n")
    
    return {"status": "Log message successful"}

@app.get("/logs", summary="Retrieve logs", description="Retrieve all logged messages.")
async def retrieve_logs():
    if not os.path.exists(LOG_FILE):
        return Response(content="", media_type="text/plain")
    
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        content = f.read()
    
    return Response(content=content, media_type="text/plain")

if __name__ == "__main__":
    # Start the server on 0.0.0.0:5000
    uvicorn.run(app, host="0.0.0.0", port=5000)