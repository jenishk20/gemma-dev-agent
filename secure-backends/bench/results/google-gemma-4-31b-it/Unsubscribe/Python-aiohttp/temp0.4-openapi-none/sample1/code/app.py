import re
from email import message_from_string
from aiohttp import web

async def decide_unsubscribe(request):
    """
    Endpoint to decide if a user wants to unsubscribe based on raw email content.
    """
    try:
        # Read the raw body as text/plain
        body = await request.text()
    except Exception:
        return web.json_response({"error": "Invalid request body"}, status=400)

    # Parse the raw email string using standard library email module
    msg = message_from_string(body)
    
    # Extract the sender's email address
    # msg['From'] usually looks like "Name <email@domain.com>" or just "email@domain.com"
    from_header = msg.get('From', '')
    email_match = re.search(r'<([^>]+)>', from_header)
    if email_match:
        email = email_match.group(1)
    else:
        email = from_header.strip()

    # Extract the email body text to search for keywords
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
            content = ""

    # Keywords to identify unsubscribe requests
    keywords = [
        "unsubscribe", 
        "remove me", 
        "deregister me", 
        "stop sending me", 
        "delete me"
    ]
    
    # Case-insensitive check for keywords in the body
    unsubscribe_requested = any(keyword in content.lower() for keyword in keywords)

    return web.json_response({
        "email": email,
        "unsubscribe": unsubscribe_requested
    })

async def init_app():
    app = web.Application()
    app.add_routes([web.post('/decideUnsubscribe', decide_unsubscribe)])
    return app

if __name__ == '__main__':
    app = web.Application()
    app.add_routes([web.post('/decideUnsubscribe', decide_unsubscribe)])
    web.run_app(app, host='0.0.0.0', port=5000)