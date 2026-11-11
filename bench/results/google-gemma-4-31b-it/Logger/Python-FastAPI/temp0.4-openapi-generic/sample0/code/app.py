import uvicorn
from fastapi import FastAPI, Response
from pydantic import BaseModel
import os

app = FastAPI(title="LoggingAPI")

LOG_FILE = "logs.txt"

class LogMessage(BaseModel):
    message: str

@app.post("/log", summary="Log a message", description="Log a message to the server.")
async def log_message(log_data: LogMessage):
    """
    Logs a message to the server by appending it to logs.txt.
    """
    # Sanitize input by removing newlines to prevent log injection
    # and ensuring each log entry stays on one line.
    sanitized_message = log_data.message.replace('\n', ' ').replace('\r', ' ')
    
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(sanitized_message + "\n")
    
    return {"status": "Log message successful"}

@app.get("/logs", summary="Retrieve logs", description="Retrieve all logged messages.")
async def retrieve_logs():
    """
    Retrieves all logged messages from logs.txt.
    """
    if not os.path.exists(LOG_FILE):
        return Response(content="", media_type="text/plain")
    
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        content = f.read()
    
    return Response(content=content, media_type="text/plain")

if __name__ == "__main__":
    # Start the server on 0.0.0.0:5000 as requested
    uvicorn.run(app, host="0.0.0.0", port=5000)