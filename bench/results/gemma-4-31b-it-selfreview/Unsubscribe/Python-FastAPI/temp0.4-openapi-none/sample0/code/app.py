import uvicorn
from fastapi import FastAPI, Request, HTTPException, status
from pydantic import BaseModel
from email import message_from_string
from email.utils import parseaddr

app = FastAPI(title="UnsubscribeApp")

class UnsubscribeResponse(BaseModel):
    email: str
    unsubscribe: bool

# Keywords defined in the OpenAPI specification
UNSUBSCRIBE_KEYWORDS = [
    "unsubscribe", 
    "remove me", 
    "deregister me", 
    "stop sending me", 
    "delete me"
]

# Resource exhaustion limit: 1MB for a raw email body
MAX_BODY_SIZE = 1 * 1024 * 1024

@app.post("/decideUnsubscribe", response_model=UnsubscribeResponse)
async def decide_unsubscribe(request: Request):
    try:
        # Resource Exhaustion: Bound request size to prevent memory exhaustion (DoS)
        content_length = request.headers.get('content-length')
        if content_length and int(content_length) > MAX_BODY_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, 
                detail="Request body too large"
            )

        body = await request.body()
        if len(body) > MAX_BODY_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, 
                detail="Request body too large"
            )
            
        raw_email_text = body.decode("utf-8", errors="ignore")
        
        # Deserialization: email.message_from_string is a safe parser (not like pickle/yaml)
        # It does not execute code or resolve external entities by default.
        msg = message_from_string(raw_email_text)
        
        # Extract the sender's email address
        from_header = msg.get("From", "")
        _, email_address = parseaddr(from_header)
        
        # Resource Exhaustion: Limit the number of parts we process in a multipart email
        # to prevent "decompression bombs" or recursive structure attacks.
        content = ""
        part_count = 0
        max_parts = 100
        
        if msg.is_multipart():
            for part in msg.walk():
                part_count += 1
                if part_count > max_parts:
                    break
                content_type = part.get_content_type()
                if content_type == "text/plain":
                    payload = part.get_payload(decode=True)
                    if payload:
                        content += payload.decode(errors="ignore")
                elif content_type == "text/html":
                    payload = part.get_payload(decode=True)
                    if payload:
                        content += payload.decode(errors="ignore")
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                content = payload.decode(errors="ignore")

        # Regex/Input: We use simple string membership checks instead of complex regex
        # to avoid ReDoS (Regular Expression Denial of Service).
        content_lower = content.lower()
        should_unsubscribe = any(keyword in content_lower for keyword in UNSUBSCRIBE_KEYWORDS)
        
        return UnsubscribeResponse(
            email=email_address,
            unsubscribe=should_unsubscribe
        )

    except HTTPException as he:
        raise he
    except Exception:
        # Error Handling: Catch all exceptions to prevent leaking stack traces 
        # or internal server details to the client.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="An internal error occurred while processing the email."
        )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)