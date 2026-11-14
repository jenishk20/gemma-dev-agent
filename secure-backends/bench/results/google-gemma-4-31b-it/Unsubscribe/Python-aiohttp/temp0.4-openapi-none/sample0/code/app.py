import re
from email import message_from_string
from aiohttp import web

# Keywords defined in the OpenAPI specification
UNSUBSCRIBE_KEYWORDS = [
    "unsubscribe",
    "remove me",
    "deregister me",
    "stop sending me",
    "delete me"
]

async def decide_unsubscribe(request):
    """
    Endpoint to decide if a user wants to be unsubscribed based on raw email content.
    """
    try:
        # Read the raw body as text/plain as per OpenAPI spec
        body = await request.text()
    except Exception:
        return web.json_response({"error": "Invalid request body"}, status=400)

    # Parse the raw email string using standard library email module
    msg = message_from_string(body)
    
    # Extract the sender's email address
    # msg['From'] typically looks like "Name <email@example.com>" or just "email@example.com"
    from_header = msg.get('From', '')
    email_match = re.search(r'([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)', from_header)
    email = email_match.group(1) if email_match else None

    # Extract the body of the email to check for keywords
    # We handle both plain text and multipart emails
    content = ""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == 'text/plain':
                try:
                    content += part.get_payload(decode=True).decode(errors='ignore')
                except Exception:
                    pass
    else:
        try:
            content = msg.get_payload(decode=True).decode(errors='ignore')
        except Exception:
            content = str(msg.get_payload())

    # Check if any of the unsubscribe keywords are present in the content (case-insensitive)
    content_lower = content.lower()
    should_unsubscribe = any(keyword in content_lower for keyword in UNSUBSCRIBE_KEYWORDS)

    return web.json_response({
        "email": email,
        "unsubscribe": should_unsubscribe
    })

app = web.Application()
app.add_routes([web.post('/decideUnsubscribe', decide_unsubscribe)])

if __name__ == '__main__':
    web.run_app(app, host='0.0.0.0', port=5000)