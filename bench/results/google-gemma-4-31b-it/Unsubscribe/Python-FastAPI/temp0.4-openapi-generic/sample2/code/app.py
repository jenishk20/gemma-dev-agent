import uvicorn
from fastapi import FastAPI, Request, Response
from pydantic import BaseModel, EmailStr
from email import message_from_string
from email.utils import parseaddr

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
    # Read raw body as text/plain as per schema
    body = await request.body()
    raw_email_text = body.decode("utf-8", errors="ignore")
    
    if not raw_email_text:
        return UnsubscribeDecision(email="unknown", unsubscribe=False)

    # Parse the raw email using standard library email module
    msg = message_from_string(raw_email_text)
    
    # Extract sender email address
    from_header = msg.get("From", "")
    name, email = parseaddr(from_header)
    
    # If email is empty, we can't reliably unsubscribe
    if not email:
        email = "unknown"

    # Extract the body content to check for keywords
    # We iterate through parts to handle multipart emails (text/plain, text/html)
    content = ""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == "text/plain" or content_type == "text/html":
                try:
                    content += part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8", errors="ignore")
                except Exception:
                    continue
    else:
        content = msg.get_payload(decode=True).decode(msg.get_content_charset() or "utf-8", errors="ignore")

    # Decision logic: check if any keyword exists in the email body (case-insensitive)
    content_lower = content.lower()
    should_unsubscribe = any(keyword in content_lower for keyword in UNSUBSCRIBE_KEYWORDS)

    return UnsubscribeDecision(email=email, unsubscribe=should_unsubscribe)

if __name__ == "__main__":
    # Start the server on 0.0.0.0:5000 as requested
    uvicorn.run(app, host="0.0.0.0", port=5000)