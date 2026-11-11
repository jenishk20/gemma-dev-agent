import uvicorn
from fastapi import FastAPI, Request, Response
from pydantic import BaseModel
from email import message_from_string
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

def extract_email_and_decision(raw_email_text: str):
    # Parse the raw email string using the standard library email module
    msg = message_from_string(raw_email_text)
    
    # Extract the sender's email address
    # msg['From'] usually looks like "Name <email@domain.com>"
    from_header = msg.get('From', '')
    email_match = re.search(r'([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)', from_header)
    email = email_match.group(1) if email_match else "unknown"

    # Extract the body of the email to check for keywords
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
            body = str(msg)

    # Case-insensitive check for any of the unsubscribe keywords
    body_lower = body.lower()
    should_unsubscribe = any(keyword in body_lower for keyword in UNSUBSCRIBE_KEYWORDS)
    
    return email, should_unsubscribe

@app.post("/decideUnsubscribe", response_model=UnsubscribeDecision)
async def decide_unsubscribe(request: Request):
    """
    Expects a raw E-Mail from a user and returns whether the user 
    should be unsubscribed together with the user's E-Mail address.
    """
    # The OpenAPI spec defines the requestBody as text/plain
    body_bytes = await request.body()
    raw_email_text = body_bytes.decode('utf-8', errors='ignore')
    
    if not raw_email_text:
        # Handle empty body case
        return UnsubscribeDecision(email="unknown", unsubscribe=False)
    
    email, unsubscribe = extract_email_and_decision(raw_email_text)
    
    return UnsubscribeDecision(email=email, unsubscribe=unsubscribe)

if __name__ == "__main__":
    # Start the webserver on port 0.0.0.0:5000 as requested
    uvicorn.run(app, host="0.0.0.0", port=5000)