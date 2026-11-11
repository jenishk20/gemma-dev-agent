import os
from aiohttp import web

# Configuration
SONGS_DIRECTORY = "/var/songs"
HOST = "0.0.0.0"
PORT = 5000

async def handle_download(request):
    """
    Handles the POST /download endpoint.
    Expects JSON body with a 'filename' property.
    """
    try:
        data = await request.json()
    except Exception:
        return web.Response(text="Invalid JSON input", status=400)

    if not data or not isinstance(data, dict):
        return web.Response(text="Invalid input", status=400)

    filename = data.get("filename")
    if not filename or not isinstance(filename, str):
        return web.Response(text="Missing or invalid filename", status=400)

    # Security: Prevent directory traversal attacks by normalizing and checking the path
    # Ensure the requested file is actually inside the SONGS_DIRECTORY
    safe_filename = os.path.basename(filename)
    file_path = os.path.join(SONGS_DIRECTORY, safe_filename)

    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        return web.Response(text="File does not exist", status=404)

    # Stream the file content using a FileResponse
    # This is more efficient than reading the whole file into memory
    return web.FileResponse(file_path, content_type="audio/mpeg")

async def init_app():
    app = web.Application()
    app.add_routes([web.post('/download', handle_download)])
    return app

if __name__ == "__main__":
    app = None
    # We use a helper to run the app since init_app is async
    import asyncio
    
    async def main():
        global app
        app = await init_app()
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, HOST, PORT)
        await site.start()
        print(f"Server started at http://{HOST}:{PORT}")
        # Keep the server running forever
        await asyncio.Event().wait()

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass