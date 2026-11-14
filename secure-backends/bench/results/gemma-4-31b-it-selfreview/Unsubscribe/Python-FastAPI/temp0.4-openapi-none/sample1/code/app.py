import uvicorn
from fastapi import FastAPI, Request, HTTPException, status
from pydantic import BaseModel
from email import message_from_string
from email.utils import parseaddr

app = FastAPI(title="UnsubscribeApp")

class UnsubscribeResponse(BaseModel):
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

# Resource exhaustion protection: Limit the size of the raw email body (e.g., 1MB)
MAX_REQUEST_SIZE = 1_048_576 

def extract_email_from_raw(raw_email: str) -> str:
    """Extracts the sender's email address from a raw email string."""
    try:
        # message_from_string is a safe parser that doesn't execute code
        msg = message_from_string(raw_email)
        from_header = msg.get("From", "")
        name, addr = parseaddr(from_header)
        return addr if addr else ""
    except Exception:
        return ""

def should_unsubscribe(raw_email: str) -> bool:
    """Checks if the email body contains any of the unsubscribe keywords."""
    try:
        msg = message_from_string(raw_email)
        body = ""
        if msg.is_multipart():
            # walk() is an iterator, we limit the number of parts to prevent 
            # "decompression bomb" style resource exhaustion in nested emails
            parts_processed = 0
            for part in msg.walk():
                parts_processed += 1
                if parts_processed > 100: 
                    break
                content_type = part.get_content_type()
                if content_type == "text/plain":
                    payload = part.get_payload(decode=True)
                    if payload:
                        body += payload.decode(errors='ignore')
                elif content_type == "text/html":
                    payload = part.get_payload(decode=True)
                    if payload:
                        body += payload.decode(errors='ignore')
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                body = payload.decode(errors='ignore')
        
        body_lower = body.lower()
        return any(keyword in body_lower for keyword in UNSUBSCRIBE_KEYWORDS)
    except Exception:
        return False

@app.post("/decideUnsubscribe", response_model=UnsubscribeResponse)
async def decide_unsubscribe(request: Request):
    # Resource Exhaustion: Bound the request size
    content_length = request.headers.get('content-length')
    if content_length and int(content_length) > MAX_REQUEST_SIZE:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)

    try:
        raw_body = await request.body()
        if len(raw_body) > MAX_REQUEST_SIZE:
            raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)
            
        email_text = raw_body.decode('utf-8', errors='ignore')
        
        email_address = extract_email_from_raw(email_text)
        decision = should_unsubscribe(email_text)
        
        return UnsubscribeResponse(
            email=email_address,
            unsubscribe=decision
        )
    except HTTPException as he:
        raise he
    except Exception:
        # Error handling: Catch all exceptions to prevent leaking stack traces
        # Return a generic 500 or 400 depending on the nature of the failure
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="An internal error occurred while processing the email."
        )

if __name__ == "__main__":
    # Run on 0.0.0.0:5000 as requested
    uvicorn.run(app, host="0.0.0.0", port=5000)