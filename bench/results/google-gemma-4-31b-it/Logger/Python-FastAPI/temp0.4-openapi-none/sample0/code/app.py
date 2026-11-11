import uvicorn
from fastapi import FastAPI, Response
from pydantic import BaseModel
from typing import Optional

app = FastAPI(title="LoggingAPI", version="1.0.11")

LOG_FILE = "logs.txt"

class LogRequest(BaseModel):
    message: str

@app.post("/log", summary="Log a message", description="Log a message to the server.")
async def log_message(request: LogRequest):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(request.message + "\n")
    return {"status": "Log message successful"}

@app.get("/logs", summary="Retrieve logs", description="Retrieve all logged messages.")
async def retrieve_logs():
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        content = ""
    
    return Response(content=content, media_type="text/plain")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)