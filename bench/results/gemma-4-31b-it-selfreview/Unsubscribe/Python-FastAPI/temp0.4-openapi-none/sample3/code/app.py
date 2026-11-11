import uvicorn
from fastapi import FastAPI, Request, HTTPException, status
from pydantic import BaseModel
from email import message_from_string
from email.utils import parseaddr

app = FastAPI(title="UnsubscribeApp")

class UnsubscribeResponse(BaseModel):
    email: str
    unsubscribe: bool

# Keywords as specified in the OpenAPI description
UNSUBSCRIBE_KEYWORDS = [
    "unsubscribe",
    "remove me",
    "deregister me",
    "stop sending me",
    "delete me"
]

# Resource exhaustion: Limit the maximum size of the request body to prevent DoS (e.g., 1MB)
MAX_BODY_SIZE = 1 * 1024 * 1024 

@app.post("/decideUnsubscribe", response_model=UnsubscribeResponse)
async def decide_unsubscribe(request: Request):
    try:
        # Resource exhaustion: Check content-length header first
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > MAX_BODY_SIZE:
            raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)

        # Read raw body
        body = await request.body()
        
        # Resource exhaustion: Verify actual body size
        if len(body) > MAX_BODY_SIZE:
            raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)
            
        raw_email_text = body.decode("utf-8", errors="ignore")
        
        # Parse the email using standard library. 
        # email.message_from_string is generally safe against XML-style XXE as it doesn't use an XML parser.
        msg = message_from_string(raw_email_text)
        
        # Extract the sender's email address
        from_header = msg.get("From", "")
        name, email = parseaddr(from_header)
        
        # If no email was found in the header, we provide a default
        if not email:
            email = "unknown"

        # Extract the email body to check for keywords
        content = ""
        if msg.is_multipart():
            # Resource exhaustion: Limit the number of parts to prevent "decompression bombs" or recursive structures
            parts_processed = 0
            for part in msg.walk():
                parts_processed += 1
                if parts_processed > 100: 
                    break
                
                content_type = part.get_content_type()
                if content_type == "text/plain" or content_type == "text/html":
                    try:
                        # decode=True handles quoted-printable/base64 encoding
                        payload = part.get_payload(decode=True)
                        if payload:
                            content += payload.decode("utf-8", errors="ignore")
                    except Exception:
                        pass
        else:
            payload = msg.get_payload()
            if isinstance(payload, bytes):
                content = payload.decode("utf-8", errors="ignore")
            elif isinstance(payload, str):
                content = payload
            else:
                content = str(payload)

        # Decision logic: check if any keyword exists in the content (case-insensitive)
        content_lower = content.lower()
        should_unsubscribe = any(keyword in content_lower for keyword in UNSUBSCRIBE_KEYWORDS)

        return UnsubscribeResponse(email=email, unsubscribe=should_unsubscribe)

    except HTTPException as he:
        raise he
    except Exception:
        # Error handling: Catch all other exceptions to prevent leaking stack traces
        # Return a generic 400 error for malformed input
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Invalid request payload"
        )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)