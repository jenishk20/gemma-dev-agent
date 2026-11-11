import uvicorn
from fastapi import FastAPI, Request, Response
from pydantic import BaseModel
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
    # Read the raw body as text/plain as per schema
    body = await request.body()
    raw_email_text = body.decode("utf-8", errors="ignore")
    
    if not raw_email_text:
        return UnsubscribeDecision(email="", unsubscribe=False)

    # Parse the raw email using standard library
    msg = message_from_string(raw_email_text)
    
    # Extract the sender's email address
    from_header = msg.get("From", "")
    name, email = parseaddr(from_header)
    
    # Extract the body of the email for keyword searching
    # We iterate through parts to handle multipart emails
    email_content = ""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    email_content += payload.decode("utf-8", errors="ignore") + " "
            elif content_type == "text/html":
                # Fallback to HTML if plain text is missing
                if not email_content:
                    payload = part.get_payload(decode=True)
                    if payload:
                        email_content += payload.decode("utf-8", errors="ignore") + " "
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            email_content = payload.decode("utf-8", errors="ignore")

    # If we couldn't get a body from the payload, check the raw text as a fallback
    if not email_content:
        email_content = raw_email_text

    # Decision logic: check if any keyword exists in the content (case-insensitive)
    content_lower = email_content.lower()
    should_unsubscribe = any(keyword in content_lower for keyword in UNSUBSCRIBE_KEYWORDS)

    return UnsubscribeDecision(
        email=email,
        unsubscribe=should_unsubscribe
    )

if __name__ == "__main__":
    # Start the server on 0.0.0.0:5000 as requested
    uvicorn.run(app, host="0.0.0.0", port=5000)