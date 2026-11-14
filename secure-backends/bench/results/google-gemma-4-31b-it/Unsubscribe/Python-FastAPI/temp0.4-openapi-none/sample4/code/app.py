import uvicorn
from fastapi import FastAPI, Request
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

def extract_email_and_decision(raw_email_text: str):
    # Parse the raw email string using standard library email module
    msg = message_from_string(raw_email_text)
    
    # Extract the 'From' address
    # msg['From'] usually looks like "Name <email@example.com>"
    from_header = msg.get('From', '')
    email_match = re.search(r'<([^>]+)>', from_header)
    if email_match:
        email = email_match.group(1)
    else:
        email = from_header.strip()

    # Extract body content to check for keywords
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
            body = str(msg.get_payload())

    # Decision logic: check if any keyword exists in the body (case-insensitive)
    body_lower = body.lower()
    should_unsubscribe = any(keyword in body_lower for keyword in UNSUBSCRIBE_KEYWORDS)
    
    return email, should_unsubscribe

@app.post("/decideUnsubscribe", response_model=UnsubscribeResponse)
async def decide_unsubscribe(request: Request):
    # The OpenAPI schema specifies text/plain for the request body
    raw_body = await request.body()
    email_text = raw_body.decode('utf-8', errors='ignore')
    
    email, unsubscribe = extract_email_and_decision(email_text)
    
    return UnsubscribeResponse(email=email, unsubscribe=unsubscribe)

if __name__ == "__main__":
    # Start the webserver on port 0.0.0.0:5000 as requested
    uvicorn.run(app, host="0.0.0.0", port=5000)