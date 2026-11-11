import uvicorn
from fastapi import FastAPI, Request
from pydantic import BaseModel
from email import message_from_string
from email.utils import parseaddr
import re

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

@app.post("/decideUnsubscribe", response_model=UnsubscribeResponse)
async def decide_unsubscribe(request: Request):
    # Read the raw body as text/plain
    body = await request.body()
    raw_email_text = body.decode("utf-8", errors="ignore")
    
    # Parse the email using the standard library email module
    msg = message_from_string(raw_email_text)
    
    # Extract the sender's email address
    # parseaddr returns a tuple (real_name, email)
    from_header = msg.get("From", "")
    _, email_address = parseaddr(from_header)
    
    # Extract the body of the email to check for keywords
    # We iterate through parts to handle multipart emails
    content = ""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == "text/plain":
                content += part.get_payload(decode=True).decode(errors="ignore")
            elif content_type == "text/html":
                # Fallback to HTML if plain text is missing
                content += part.get_payload(decode=True).decode(errors="ignore")
    else:
        content = msg.get_payload(decode=True).decode(errors="ignore")

    # Decision logic: check if any keyword exists in the content (case-insensitive)
    content_lower = content.lower()
    should_unsubscribe = any(keyword in content_lower for keyword in UNSUBSCRIBE_KEYWORDS)
    
    return UnsubscribeResponse(
        email=email_address,
        unsubscribe=should_unsubscribe
    )

if __name__ == "__main__":
    # Start the webserver on port 0.0.0.0:5000
    uvicorn.run(app, host="0.0.0.0", port=5000)