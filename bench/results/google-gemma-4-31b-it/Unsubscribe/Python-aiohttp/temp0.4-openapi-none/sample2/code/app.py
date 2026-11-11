import re
from email import message_from_string
from aiohttp import web

async def decide_unsubscribe(request):
    """
    Endpoint to decide if a raw email request is an unsubscribe request.
    """
    try:
        # Read the raw body as text/plain as per OpenAPI spec
        body = await request.text()
    except Exception:
        return web.json_response({"error": "Invalid request body"}, status=400)

    if not body:
        return web.json_response({"email": None, "unsubscribe": False}, status=200)

    # Parse the raw email string using standard library email module
    msg = message_from_string(body)
    
    # Extract the sender's email address
    # The 'From' header usually looks like "Name <email@domain.com>"
    from_header = msg.get('From', '')
    email_match = re.search(r'<([^>]+)>', from_header)
    if email_match:
        email_address = email_match.group(1)
    else:
        email_address = from_header.strip()

    # Extract the email body for keyword analysis
    # Handle multipart emails by iterating through payloads
    content_text = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == 'text/plain':
                try:
                    content_text += part.get_payload(decode=True).decode(errors='ignore')
                except Exception:
                    pass
    else:
        try:
            content_text = msg.get_payload(decode=True).decode(errors='ignore')
        except Exception:
            content_text = str(msg.get_payload())

    # Keywords to identify unsubscribe requests
    keywords = [
        "unsubscribe", 
        "remove me", 
        "deregister me", 
        "stop sending me", 
        "delete me"
    ]
    
    # Case-insensitive check for keywords in the body
    content_lower = content_text.lower()
    should_unsubscribe = any(keyword in content_lower for keyword in keywords)

    return web.json_response({
        "email": email_address,
        "unsubscribe": should_unsubscribe
    })

async def init_app():
    app = web.Application()
    app.add_routes([web.post('/decideUnsubscribe', decide_unsubscribe)])
    return app

if __name__ == '__main__':
    app = web.Application()
    app.add_routes([web.post('/decideUnsubscribe', decide_unsubscribe)])
    web.run_app(app, host='0.0.0.0', port=5000)