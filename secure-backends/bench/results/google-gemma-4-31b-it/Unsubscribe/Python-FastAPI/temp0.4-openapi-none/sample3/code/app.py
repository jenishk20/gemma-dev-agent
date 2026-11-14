import uvicorn
from fastapi import FastAPI, Request
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

@app.post("/decideUnsubscribe", response_model=UnsubscribeResponse)
async def decide_unsubscribe(request: Request):
    # Read raw body as text/plain
    body = await request.body()
    raw_email_text = body.decode("utf-8", errors="ignore")
    
    # Parse the email using standard library
    msg = message_from_string(raw_email_text)
    
    # Extract the sender's email address
    from_header = msg.get("From", "")
    name, email = parseaddr(from_header)
    
    # If no email was found in the header, we can't identify the user
    if not email:
        email = "unknown"

    # Extract the email body to check for keywords
    # We iterate through parts to handle multipart emails (text/plain or text/html)
    content = ""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == "text/plain" or content_type == "text/html":
                try:
                    content += part.get_payload(decode=True).decode("utf-8", errors="ignore")
                except Exception:
                    pass
    else:
        content = msg.get_payload()

    # Decision logic: check if any keyword exists in the content (case-insensitive)
    content_lower = content.lower()
    should_unsubscribe = any(keyword in content_lower for keyword in UNSUBSCRIBE_KEYWORDS)

    return UnsubscribeResponse(email=email, unsubscribe=should_unsubscribe)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)