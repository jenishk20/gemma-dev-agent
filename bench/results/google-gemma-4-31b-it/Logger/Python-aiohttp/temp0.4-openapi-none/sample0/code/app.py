import asyncio
from aiohttp import web

LOG_FILE = "logs.txt"

async def handle_post_log(request):
    """
    POST /log: Log a message to the server.
    Expects JSON: {"message": "..."}
    """
    try:
        data = await request.json()
        message = data.get("message")
        
        if message is None:
            return web.json_response({"error": "Missing 'message' field"}, status=400)
        
        # Append the message to the text file
        # Using standard open() in a thread pool via loop.run_in_executor 
        # to avoid blocking the event loop for I/O
        loop = asyncio.get_event_loop()
        def write_log():
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(str(message) + "\n")
        
        await loop.run_in_executor(None, write_log)
        
        return web.Response(status=200)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=400)

async def handle_get_logs(request):
    """
    GET /logs: Retrieve all logged messages.
    Returns text/plain.
    """
    loop = asyncio.get_event_loop()
    def read_logs():
        try:
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            return ""

    content = await loop.run_in_executor(None, read_logs)
    return web.Response(text=content, content_type="text/plain")

async def init_app():
    app = web.Application()
    app.add_routes([
        web.post('/log', handle_post_log),
        web.get('/logs', handle_get_logs),
    ])
    return app

if __name__ == "__main__":
    app = asyncio.run(init_app()) # This is a helper, but we need to run the server
    # Re-initializing for the runner
    app = web.Application()
    app.add_routes([
        web.post('/log', handle_post_log),
        web.get('/logs', handle_get_logs),
    ])
    web.run_app(app, host='0.0.0.0', port=5000)