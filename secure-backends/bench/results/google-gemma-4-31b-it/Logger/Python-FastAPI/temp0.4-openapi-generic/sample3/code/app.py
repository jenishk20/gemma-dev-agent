import uvicorn
from fastapi import FastAPI, Response
from pydantic import BaseModel, Field

# Initialize FastAPI app
app = FastAPI(title="LoggingAPI", version="1.0.11")

# Define the log file path
LOG_FILE = "logs.txt"

# Request model for the /log endpoint
class LogMessage(BaseModel):
    message: str = Field(..., example="This is a log message")

@app.post("/log", summary="Log a message", description="Log a message to the server.")
async def log_message(log_data: LogMessage):
    """
    Appends a log message to the logs.txt file.
    Ensures the message is stripped of newlines to maintain one log per line.
    """
    # Sanitize input to prevent log injection (removing newlines)
    sanitized_message = log_data.message.replace('\n', ' ').replace('\r', ' ')
    
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(sanitized_message + "\n")
    
    return {"status": "Log message successful"}

@app.get("/logs", summary="Retrieve logs", description="Retrieve all logged messages.")
async def retrieve_logs():
    """
    Reads all messages from logs.txt and returns them as a plain text response.
    """
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        # Return empty string if file hasn't been created yet
        content = ""
    
    # Return as text/plain as specified in the OpenAPI schema
    return Response(content=content, media_type="text/plain")

if __name__ == "__main__":
    # Start the server on 0.0.0.0:5000
    uvicorn.run(app, host="0.0.0.0", port=5000)