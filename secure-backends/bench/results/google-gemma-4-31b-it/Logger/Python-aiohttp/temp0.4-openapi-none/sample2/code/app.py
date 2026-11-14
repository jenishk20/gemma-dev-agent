import asyncio
from aiohttp import web

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
            return web.json_response({"error": "Missing 'message' field"}, status=400)

        # Append the message to the text file
        # Using a synchronous write here as standard open() is common for simple tasks, 
        # but in a production aiohttp app, one might use aiofiles.
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
    app = asyncio.run(init_app()) # This is a helper logic, actually we need to run the app
    # Correct way to run aiohttp server:
    async def start_server():
        app = await init_app()
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', 5000)
        await site.start()
        print("Server started at http://0.0.0.0:5000")
        await asyncio.Event().wait()

    try:
        asyncio.run(start_server())
    except KeyboardInterrupt:
        pass