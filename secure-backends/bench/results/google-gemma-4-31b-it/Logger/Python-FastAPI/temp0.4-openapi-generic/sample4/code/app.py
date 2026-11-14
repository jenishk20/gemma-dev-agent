import uvicorn
from fastapi import FastAPI, Response
from pydantic import BaseModel
import os

app = FastAPI(title="LoggingAPI")

LOG_FILE = "logs.txt"

class LogRequest(BaseModel):
    message: str

@app.post("/log", summary="Log a message", description="Log a message to the server.")
async def log_message(request: LogRequest):
    # Sanitize input by removing newline characters to prevent log injection
    # and ensure each log entry stays on one line.
    sanitized_message = request.message.replace('\n', ' ').replace('\r', ' ')
    
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
    # Start the server on 0.0.0.0:5000 as requested
    uvicorn.run(app, host="0.0.0.0", port=5000)