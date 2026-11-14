import asyncio
import aiohttp
from aiohttp import web
import aiofiles # Note: aiofiles is not in the list, using standard open in thread for simplicity or blocking for a simple service
import os

LOG_FILE = "logs.txt"

async def handle_post_log(request):
    """
    POST /log
    Expects JSON: {"message": "..."}
    """
    try:
        data = await request.json()
        message = data.get("message")
        if message is None:
            return web.json_response({"error": "Missing message field"}, status=400)
        
        # Write to file (blocking call in a simple implementation, 
        # but for a production app we'd use aiofiles or a queue)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"{message}\n")
            
        return web.Response(status=200)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=400)

async def handle_get_logs(request):
    """
    GET /logs
    Returns the content of logs.txt as plain text.
    """
    if not os.path.exists(LOG_FILE):
        return web.Response(text="", content_type="text/plain", status=200)
    
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        content = f.read()
        
    return web.Response(text=content, content_type="text/plain", status=200)

async def init_app():
    app = web.Application()
    app.add_routes([
        web.post('/log', handle_post_log),
        web.get('/logs', handle_get_logs),
    ])
    return app

if __name__ == "__main__":
    app = asyncio.run(init_app()) # This is not how aiohttp usually starts, let's fix it
    
# Correcting the runner for aiohttp
def main():
    app = web.Application()
    app.add_routes([
        web.post('/log', handle_post_log),
        web.get('/logs', handle_get_logs),
    ])
    web.run_app(app, host='0.0.0.0', port=5000)

if __name__ == "__main__":
    main()