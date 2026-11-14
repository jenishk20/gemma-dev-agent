import asyncio
from aiohttp import web
from email import message_from_string
from email.utils import parseaddr

async def handle_decide_unsubscribe(request):
    """
    Endpoint to decide whether a user requested to be unsubscribed.
    Expects raw email text in the request body.
    """
    try:
        # Read the raw body as text
        body = await request.text()
    except Exception:
        return web.json_response({"error": "Invalid request body"}, status=400)

    if not body:
        return web.json_response({"error": "Empty request body"}, status=400)

    # Parse the raw email string using standard library email module
    msg = message_from_string(body)
    
    # Extract the sender's email address
    from_header = msg.get('From', '')
    name, email = parseaddr(from_header)
    
    # If email couldn't be parsed, we can't fulfill the request properly
    if not email:
        return web.json_response({"error": "Could not extract sender email"}, status=400)

    # Extract the email body for keyword searching
    # We look through all parts of the email (handling multipart)
    content = ""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == 'text/plain':
                try:
                    content += part.get_payload(decode=True).decode(errors='ignore')
                except Exception:
                    pass
            elif content_type == 'text/html':
                try:
                    content += part.get_payload(decode=True).decode(errors='ignore')
                except Exception:
                    pass
    else:
        try:
            content = msg.get_payload(decode=True).decode(errors='ignore')
        except Exception:
            content = str(msg.get_payload())

    # Keywords to identify unsubscribe requests
    unsubscribe_keywords = [
        "unsubscribe", 
        "remove me", 
        "deregister me", 
        "stop sending me", 
        "delete me"
    ]
    
    # Check if any keyword is present in the content (case-insensitive)
    content_lower = content.lower()
    should_unsubscribe = any(keyword in content_lower for keyword in unsubscribe_keywords)

    return web.json_response({
        "email": email,
        "unsubscribe": should_unsubscribe
    })

async def init_app():
    app = web.Application()
    app.add_routes([web.post('/decideUnsubscribe', handle_decide_unsubscribe)])
    return app

if __name__ == '__main__':
    app = asyncio.run(init_app()) # This is a helper, but we need to run the server
    # Correct way to run aiohttp server in a single file
    async def start_server():
        app = await init_app()
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', 5000)
        await site.start()
        print("Server started at http://0.0.0.0:5000")
        # Keep the server running
        await asyncio.Event().wait()

    try:
        asyncio.run(start_server())
    except KeyboardInterrupt:
        pass