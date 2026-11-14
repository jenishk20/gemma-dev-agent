import uvicorn
from fastapi import FastAPI, Request, Response
from pydantic import BaseModel, EmailStr
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

def extract_email_and_decision(raw_email_text: str):
    """
    Parses a raw email string to extract the sender's email address 
    and determines if the content indicates an unsubscribe request.
    """
    # Parse the raw email using standard library email module
    msg = message_from_string(raw_email_text)
    
    # Extract the 'From' header
    from_header = msg.get("From", "")
    email_address = ""
    
    # Simple regex to extract email from "Name <email@domain.com>" or "email@domain.com"
    email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", from_header)
    if email_match:
        email_address = email_match.group(0)

    # Extract body content for keyword analysis
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == "text/plain":
                try:
                    body += part.get_payload(decode=True).decode(errors='ignore')
                except Exception:
                    pass
    else:
        try:
            body = msg.get_payload(decode=True).decode(errors='ignore')
        except Exception:
            body = msg.get_payload() if isinstance(msg.get_payload(), str) else ""

    # Check for keywords (case-insensitive)
    body_lower = body.lower()
    should_unsubscribe = any(keyword in body_lower for keyword in UNSUBSCRIBE_KEYWORDS)

    return email_address, should_unsubscribe

@app.post("/decideUnsubscribe", response_model=UnsubscribeResponse)
async def decide_unsubscribe(request: Request):
    """
    Expects a raw E-Mail as text/plain and returns whether the user 
    should be unsubscribed.
    """
    # Read raw body content
    body_bytes = await request.body()
    try:
        raw_email = body_bytes.decode("utf-8")
    except UnicodeDecodeError:
        # Fallback to latin-1 if utf-8 fails, common in emails
        raw_email = body_bytes.decode("latin-1")

    if not raw_email:
        # Return a default or error if body is empty
        return UnsubscribeResponse(email="", unsubscribe=False)

    email, decision = extract_email_and_decision(raw_email)
    
    return UnsubscribeResponse(email=email, unsubscribe=decision)

if __name__ == "__main__":
    # Start the server on 0.0.0.0:5000 as requested
    uvicorn.run(app, host="0.0.0.0", port=5000)