import asyncio
import aiohttp
from aiohttp import web

LOG_FILE = "logs.txt"

async def handle_post_log(request):
    """
    POST /log
    Logs a message to the server.
    """
    try:
        data = await request.json()
        message = data.get("message")
        
        if message is None:
            return web.json_response({"error": "Missing 'message' field"}, status=400)

        # Append the message to the text file
        # Using standard open() is acceptable for simple cases, 
        # but in a production aiohttp app, one might use aiofiles.
        # Given the constraints and simplicity, we use standard sync I/O.
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"{message}\n")
            
        return web.Response(status=200)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=400)

async def handle_get_logs(request):
    """
    GET /logs
    Retrieve all logged messages.
    """
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            content = f.read()
        return web.Response(text=content, content_type="text/plain")
    except FileNotFoundError:
        # If file doesn't exist yet, return empty string
        return web.Response(text="", content_type="text/plain")
    except Exception as e:
        return web.Response(text=str(e), status=500)

async def init_app():
    app = web.Application()
    app.add_routes([
        web.post('/log', handle_post_log),
        web.get('/logs', handle_get_logs),
    ])
    return app

if __name__ == "__main__":
    app = asyncio.run(init_app()) # This is a helper, but we need the runner
    # To properly start the server on 0.0.0.0:5000:
    web.run_app(asyncio.run(init_app()), port=5000, host='0.0.0.0')
# Correction: web.run_app takes the app instance directly.