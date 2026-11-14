import uvicorn
from fastapi import FastAPI, Response
from pydantic import BaseModel
import os

app = FastAPI(title="LoggingAPI", version="1.0.11")

LOG_FILE = "logs.txt"

class LogMessage(BaseModel):
    message: str

@app.post("/log", summary="Log a message", description="Log a message to the server.")
async def log_message(log_data: LogMessage):
    # Sanitize input to prevent newline injection in the text file
    # We replace newlines to ensure each log entry stays on one line
    safe_message = log_data.message.replace("\n", " ").replace("\r", " ")
    
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(safe_message + "\n")
    
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