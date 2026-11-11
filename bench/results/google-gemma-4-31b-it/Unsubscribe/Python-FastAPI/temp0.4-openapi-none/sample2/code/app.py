import uvicorn
from fastapi import FastAPI, Request
from pydantic import BaseModel
from email import message_from_string
from email.utils import parseaddr
import re

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

@app.post("/decideUnsubscribe", response_model=UnsubscribeDecision)
async def decide_unsubscribe(request: Request):
    # Read raw body as text/plain as per schema
    body = await request.body()
    raw_email_text = body.decode("utf-8", errors="ignore")
    
    # Parse the email using standard library
    msg = message_from_string(raw_email_text)
    
    # Extract sender email address
    from_header = msg.get("From", "")
    name, email_address = parseaddr(from_header)
    
    # If no email found in header, we use an empty string or a placeholder
    # but the schema expects a string.
    final_email = email_address if email_address else ""
    
    # Extract the body of the email to check for keywords
    # We iterate through parts to handle multipart emails
    content = []
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    content.append(payload.decode(errors="ignore"))
            elif content_type == "text/html":
                # Fallback to HTML if plain text is missing
                payload = part.get_payload(decode=True)
                if payload:
                    content.append(payload.decode(errors="ignore"))
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            content.append(payload.decode(errors="ignore"))
            
    full_text = " ".join(content).lower()
    
    # Decide if the user wants to unsubscribe
    should_unsubscribe = any(keyword in full_text for keyword in UNSUBSCRIBE_KEYWORDS)
    
    return UnsubscribeDecision(
        email=final_email,
        unsubscribe=should_unsubscribe
    )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)