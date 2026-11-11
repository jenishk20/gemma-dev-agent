import os
from aiohttp import web

# Configuration
SONGS_DIRECTORY = "/var/songs"
HOST = "0.0.0.0"
PORT = 5000

async def download_song(request):
    """
    Handles the POST /download endpoint.
    Expects a JSON body with a 'filename' key.
    """
    try:
        # Parse JSON body
        data = await request.json()
    except Exception:
        return web.Response(text="Invalid JSON input", status=400)

    if not data or 'filename' not in data:
        return web.Response(text="Missing 'filename' in request body", status=400)

    filename = data['filename']
    
    # Security: Prevent directory traversal attacks
    # Ensure the filename is just a name and doesn't contain path separators
    safe_filename = os.path.basename(filename)
    if safe_filename != filename:
        return web.Response(text="Invalid filename provided", status=400)

    file_path = os.path.join(SONGS_DIRECTORY, safe_filename)

    # Check if file exists and is actually a file
    if not os.path.isfile(file_path):
        return web.Response(text="File does not exist", status=404)

    # Use FileResponse for efficient streaming of the file content
    # This handles the bytestream and chunking automatically
    return web.FileResponse(file_path, content_type='audio/mpeg')

async def init_app():
    app = web.Application()
    app.add_routes([web.post('/download', download_song)])
    return app

if __name__ == "__main__":
    app = None
    # We use a loop to initialize the app and start the server
    import asyncio
    
    async def main():
        global app
        app = await init_app()
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, HOST, PORT)
        print(f"Server started at http://{HOST}:{PORT}")
        await site.start()
        
        # Keep the server running forever
        await asyncio.Event().wait()

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass