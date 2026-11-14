import uvicorn
from fastapi import FastAPI, Request
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

def extract_email_from_raw(raw_email: str) -> str:
    """Extracts the sender's email address from a raw email string."""
    try:
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
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == "text/plain":
                    body += part.get_payload(decode=True).decode(errors='ignore')
                elif content_type == "text/html":
                    body += part.get_payload(decode=True).decode(errors='ignore')
        else:
            body = msg.get_payload(decode=True).decode(errors='ignore')
        
        body_lower = body.lower()
        return any(keyword in body_lower for keyword in UNSUBSCRIBE_KEYWORDS)
    except Exception:
        return False

@app.post("/decideUnsubscribe", response_model=UnsubscribeResponse)
async def decide_unsubscribe(request: Request):
    # The OpenAPI schema specifies text/plain for the request body
    raw_body = await request.body()
    email_text = raw_body.decode('utf-8', errors='ignore')
    
    email_address = extract_email_from_raw(email_text)
    decision = should_unsubscribe(email_text)
    
    return UnsubscribeResponse(
        email=email_address,
        unsubscribe=decision
    )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)