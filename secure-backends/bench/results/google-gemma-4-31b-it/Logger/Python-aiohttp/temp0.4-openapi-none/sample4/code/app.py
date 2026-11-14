import asyncio
import aiohttp.web
import aiofiles
import os

# File to store logs
LOG_FILE = "logs.txt"

async def handle_post_log(request):
    """
    Handles POST /log
    Expects JSON body: {"message": "..."}
    """
    try:
        data = await request.json()
        message = data.get("message")
        
        if message is None:
            return aiohttp.web.json_response({"error": "Missing 'message' field"}, status=400)
        
        # Append the message to the text file with a newline
        # Using standard open in a thread or aiofiles if available. 
        # Since aiofiles isn't in the provided list, we use standard open in a blocking way 
        # or wrap it. For a simple logging service, we'll use standard open.
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"{message}\n")
            
        return aiohttp.web.Response(status=200)
    except Exception as e:
        return aiohttp.web.json_response({"error": str(e)}, status=400)

async def handle_get_logs(request):
    """
    Handles GET /logs
    Returns the content of logs.txt as text/plain
    """
    if not os.path.exists(LOG_FILE):
        return aiohttp.web.Response(text="", content_type="text/plain")
    
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        content = f.read()
        
    return aiohttp.web.Response(text=content, content_type="text/plain")

async def init_app():
    app = aiohttp.web.Application()
    app.add_routes([
        aiohttp.web.post('/log', handle_post_log),
        aiohttp.web.get('/logs', handle_get_logs),
    ])
    return app

if __name__ == "__main__":
    app = asyncio.run(init_app()) # This is a helper logic, actually we need web.run_app
    # Correct way to run aiohttp server:
    async def start_server():
        app = await init_app()
        runner = aiohttp.web.AppRunner(app)
        await runner.setup()
        site = aiohttp.web.TCPSite(runner, '0.0.0.0', 5000)
        await site.start()
        print("Server started at http://0.0.0.0:5000")
        # Keep the server running
        await asyncio.Event().wait()

    try:
        asyncio.run(start_server())
    except KeyboardInterrupt:
        pass