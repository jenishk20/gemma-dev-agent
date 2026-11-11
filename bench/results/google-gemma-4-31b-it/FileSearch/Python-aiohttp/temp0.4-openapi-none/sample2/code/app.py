import os
import asyncio
from aiohttp import web

# Configuration
BASE_DATA_DIR = "/data"
PORT = 5000
HOST = "0.0.0.0"

async def search_files_handler(request):
    """
    Handles the /search POST request.
    Searches for files based on filename or content within the /data directory.
    """
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON body"}, status=400)

    search_content = data.get("search_content")
    search_filename = data.get("search_filename")
    search_dir_rel = data.get("search_dir")

    # Determine the starting directory
    # If search_dir is provided, it's treated as relative to /data
    start_dir = BASE_DATA_DIR
    if search_dir_rel:
        # Prevent directory traversal attacks by normalizing and checking prefix
        normalized_rel = os.path.normpath(search_dir_rel).lstrip('/')
        start_dir = os.path.join(BASE_DATA_DIR, normalized_rel)
        
        # Ensure the resulting path is still within /data
        if not os.path.abspath(start_dir).startswith(os.path.abspath(BASE_DATA_DIR)):
            return web.json_response({"error": "Invalid search directory"}, status=400)

    if not os.path.exists(start_dir) or not os.path.isdir(start_dir):
        return web.json_response({"files": []}, status=200)

    matched_files = []

    # We use run_in_executor for blocking I/O operations (os.walk, open().read())
    def perform_search():
        results = []
        for root, dirs, files in os.walk(start_dir):
            for file in files:
                full_path = os.path.join(root, file)
                
                # 1. Check filename match
                # The spec says "match the filename" or "start". 
                # We'll check if the filename starts with the search_filename string.
                if search_filename and file.startswith(search_filename):
                    results.append(full_path)
                    continue
                
                # 2. Check content match
                if search_content:
                    try:
                        # We open in binary mode to avoid encoding crashes and search for bytes
                        with open(full_path, 'rb') as f:
                            content_bytes = search_content.encode('utf-8')
                            # Reading in chunks to handle large files efficiently
                            while True:
                                chunk = f.read(8192)
                                if not chunk:
                                    break
                                if content_bytes in chunk:
                                    results.append(full_path)
                                    break
                    except (OSError, IOError):
                        # Skip files that cannot be read
                        pass
        return results

    loop = asyncio.get_event_loop()
    matched_files = await loop.run_in_executor(None, perform_search)

    return web.json_response({"files": matched_files})

async def init_app():
    app = web.Application()
    app.add_routes([web.post('/search', search_files_handler)])
    return app

if __name__ == "__main__":
    app = asyncio.run(init_app()) # This is a helper, but we need the runner
    # Re-initializing for the actual runner
    async def start_server():
        app = web.Application()
        app.add_routes([web.post('/search', search_files_handler)])
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, HOST, PORT)
        await site.start()
        print(f"Server started at http://{HOST}:{PORT}")
        await asyncio.Event().wait()

    try:
        asyncio.run(start_server())
    except KeyboardInterrupt:
        pass