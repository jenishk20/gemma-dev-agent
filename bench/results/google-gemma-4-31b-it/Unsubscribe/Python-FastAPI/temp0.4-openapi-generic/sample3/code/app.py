import uvicorn
from fastapi import FastAPI, Request, Response
from pydantic import BaseModel
from email import message_from_string
from email.utils import parseaddr
import re

app = FastAPI(title="UnsubscribeApp")

class UnsubscribeDecision(BaseModel):
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

@app.post("/decideUnsubscribe", response_model=UnsubscribeDecision)
async def decide_unsubscribe(request: Request):
    """
    Expects a raw E-Mail from a user and returns whether the user 
    should be unsubscribed together with the user's E-Mail address.
    """
    # Read raw body as text/plain as per OpenAPI spec
    body = await request.body()
    raw_email_text = body.decode("utf-8", errors="ignore")
    
    if not raw_email_text:
        return UnsubscribeDecision(email="", unsubscribe=False)

    # Parse the raw email string using standard library email module
    msg = message_from_string(raw_email_text)
    
    # Extract the sender's email address
    from_header = msg.get("From", "")
    _, email_address = parseaddr(from_header)
    
    # Extract the body content to check for keywords
    # We look at all parts of the email (plain and html)
    content = ""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == "text/plain":
                content += part.get_payload(decode=True).decode("utf-8", errors="ignore")
            elif content_type == "text/html":
                content += part.get_payload(decode=True).decode("utf-8", errors="ignore")
    else:
        content = msg.get_payload(decode=True).decode("utf-8", errors="ignore")

    # Case-insensitive check for any of the unsubscribe keywords
    content_lower = content.lower()
    should_unsubscribe = any(keyword in content_lower for keyword in UNSUBSCRIBE_KEYWORDS)
    
    # Also check the subject line as a fallback
    subject_lower = msg.get("Subject", "").lower()
    if not should_unsubscribe:
        should_unsubscribe = any(keyword in subject_lower for keyword in UNSUBSCRIBE_KEYWORDS)

    return UnsubscribeDecision(
        email=email_address,
        unsubscribe=should_unsubscribe
    )

if __name__ == "__main__":
    # Start the server on 0.0.0.0:5000 as requested
    uvicorn.run(app, host="0.0.0.0", port=5000)