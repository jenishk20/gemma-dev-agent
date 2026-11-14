import uvicorn
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from email import message_from_string
from email.utils import parseaddr
import logging

# Configure logging to prevent CRLF injection in logs by replacing them
class SafeFormatter(logging.Formatter):
    def format(self, record):
        msg = super().format(record)
        return msg.replace('\n', ' ').replace('\r', ' ')

logging.basicConfig(level=logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(SafeFormatter())
logger = logging.getLogger("UnsubscribeApp")
logger.handlers = [handler]

app = FastAPI(title="UnsubscribeApp")

class UnsubscribeDecision(BaseModel):
    email: str
    unsubscribe: bool

# Keywords defined in the OpenAPI description
UNSUBSCRIBE_KEYWORDS = [
    "unsubscribe", 
    "remove me", 
    "deregister me", 
    "stop sending me", 
    "delete me"
]

# Resource exhaustion: Limit the maximum size of the request body (e.g., 1MB)
MAX_BODY_SIZE = 1 * 1024 * 1024 

@app.post("/decideUnsubscribe", response_model=UnsubscribeDecision)
async def decide_unsubscribe(request: Request):
    try:
        # Resource exhaustion: Bound request size
        content_length = request.headers.get('content-length')
        if content_length and int(content_length) > MAX_BODY_SIZE:
            raise HTTPException(status_code=413, detail="Request body too large")

        body = await request.body()
        if len(body) > MAX_BODY_SIZE:
            raise HTTPException(status_code=413, detail="Request body too large")

        raw_email_text = body.decode("utf-8", errors="ignore")
        
        # Deserialization: email.message_from_string is a parser, not a dangerous 
        # deserializer like pickle or yaml.load. It does not execute code.
        msg = message_from_string(raw_email_text)
        
        # Extract sender email address
        from_header = msg.get("From", "")
        name, email_address = parseaddr(from_header)
        
        # Sanitize email_address to prevent CRLF injection if it were to be used in headers/logs
        final_email = email_address.replace('\n', '').replace('\r', '') if email_address else ""
        
        # Extract the body of the email to check for keywords
        content = []
        # Use a limit on the number of parts to prevent "decompression bomb" style 
        # multipart emails causing resource exhaustion
        parts_count = 0
        for part in msg.walk():
            parts_count += 1
            if parts_count > 100:
                break
                
            content_type = part.get_content_type()
            if content_type == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    content.append(payload.decode(errors="ignore"))
            elif content_type == "text/html":
                payload = part.get_payload(decode=True)
                if payload:
                    content.append(payload.decode(errors="ignore"))
            
        full_text = " ".join(content).lower()
        
        # Decision logic: Using simple string containment (no regex used, avoiding ReDoS)
        should_unsubscribe = any(keyword in full_text for keyword in UNSUBSCRIBE_KEYWORDS)
        
        return UnsubscribeDecision(
            email=final_email,
            unsubscribe=should_unsubscribe
        )

    except HTTPException as he:
        raise he
    except Exception as e:
        # Error handling: Catch all exceptions to prevent leaking stack traces
        # Log the error safely
        logger.error(f"Internal error processing request: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

if __name__ == "__main__":
    # Run on 0.0.0.0:5000 as requested
    uvicorn.run(app, host="0.0.0.0", port=5000)