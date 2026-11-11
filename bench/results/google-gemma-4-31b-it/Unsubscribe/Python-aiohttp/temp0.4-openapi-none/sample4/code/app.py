import re
from aiohttp import web
from email import message_from_string
from email.utils import parseaddr

async def decide_unsubscribe(request):
    """
    Endpoint to decide whether a user requested to be unsubscribed.
    Expects raw email text in the request body.
    """
    try:
        # Read the raw body as text
        body = await request.text()
        
        # Parse the raw email string
        msg = message_from_string(body)
        
        # Extract the sender's email address
        from_header = msg.get('From', '')
        _, email_address = parseaddr(from_header)
        
        # Extract the email body text for keyword analysis
        # We look for the plain text part of the email
        content = ""
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == 'text/plain':
                    content += part.get_payload(decode=True).decode(errors='ignore')
        else:
            content = msg.get_payload(decode=True).decode(errors='ignore')

        # Keywords defined in the OpenAPI schema
        keywords = [
            "unsubscribe", 
            "remove me", 
            "deregister me", 
            "stop sending me", 
            "delete me"
        ]
        
        # Case-insensitive check for keywords in the content
        content_lower = content.lower()
        should_unsubscribe = any(keyword in content_lower for keyword in keywords)
        
        return web.json_response({
            "email": email_address,
            "unsubscribe": should_unsubscribe
        })
        
    except Exception as e:
        # Return 400 if the email is malformed or cannot be processed
        return web.json_response({"error": str(e)}, status=400)

async def init_app():
    app = web.Application()
    app.router.add_post('/decideUnsubscribe', decide_unsubscribe)
    return app

if __name__ == '__main__':
    app = web.Application()
    app.router.add_post('/decideUnsubscribe', decide_unsubscribe)
    web.run_app(app, host='0.0.0.0', port=5000)