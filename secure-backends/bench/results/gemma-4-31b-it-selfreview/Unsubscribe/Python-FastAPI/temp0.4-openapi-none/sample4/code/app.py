import uvicorn
from fastapi import FastAPI, Request, HTTPException, status
from pydantic import BaseModel
from email import message_from_string
import re

app = FastAPI(title="UnsubscribeApp")

class UnsubscribeResponse(BaseModel):
    email: str
    unsubscribe: bool

# Keywords defined in the OpenAPI schema
UNSUBSCRIBE_KEYWORDS = [
    "unsubscribe", 
    "remove me", 
    "deregister me", 
    "stop sending me", 
    "delete me"
]

# Resource exhaustion: limit the size of the raw email body to prevent MemoryError/DoS
# 1MB is generally sufficient for a mailing list reply
MAX_CONTENT_LENGTH = 1 * 1024 * 1024 

def extract_email_and_decision(raw_email_text: str):
    try:
        # Use message_from_string which is a safe parser for RFC 822/2822
        msg = message_from_string(raw_email_text)
        
        # Extract the 'From' address
        from_header = msg.get('From', '')
        # Use a non-backtracking regex or simple search to avoid ReDoS
        # The regex <([^>]+)> is simple and safe for this specific use case
        email_match = re.search(r'<([^>]+)>', from_header)
        if email_match:
            email = email_match.group(1)
        else:
            email = from_header.strip()

        # Sanitize email to prevent CRLF injection in case this is logged or used in headers elsewhere
        email = email.replace('\r', '').replace('\n', '')

        # Extract body content
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == "text/plain":
                    try:
                        # decode=True handles transfer encoding (like quoted-printable)
                        payload = part.get_payload(decode=True)
                        if payload:
                            body += payload.decode('utf-8', errors='ignore')
                    except Exception:
                        pass
        else:
            try:
                payload = msg.get_payload(decode=True)
                if payload:
                    body = payload.decode('utf-8', errors='ignore')
                else:
                    body = str(msg.get_payload())
            except Exception:
                body = str(msg.get_payload())

        # Decision logic: check if any keyword exists in the body (case-insensitive)
        body_lower = body.lower()
        should_unsubscribe = any(keyword in body_lower for keyword in UNSUBSCRIBE_KEYWORDS)
        
        return email, should_unsubscribe
    except Exception:
        # If parsing fails, we treat it as a malformed request
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Invalid email format"
        )

@app.post("/decideUnsubscribe", response_model=UnsubscribeResponse)
async def decide_unsubscribe(request: Request):
    # Resource exhaustion: Bound request size
    content_length = request.headers.get('content-length')
    if content_length and int(content_length) > MAX_CONTENT_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, 
            detail="Request body too large"
        )

    try:
        raw_body = await request.body()
        if len(raw_body) > MAX_CONTENT_LENGTH:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, 
                detail="Request body too large"
            )
        
        email_text = raw_body.decode('utf-8', errors='ignore')
        
        email, unsubscribe = extract_email_and_decision(email_text)
        
        return UnsubscribeResponse(email=email, unsubscribe=unsubscribe)
    except HTTPException as he:
        raise he
    except Exception as e:
        # Error handling: catch all other exceptions to prevent leaking stack traces
        # Return a generic 400 for malformed input as per API expectations
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="An error occurred processing the request"
        )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)