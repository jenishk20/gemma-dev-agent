import os
import asyncio
from aiohttp import web

# Configuration
BASE_DATA_DIR = "/data"
PORT = 5000
HOST = "0.0.0.0"

async def search_files_handler(request):
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    search_content = data.get("search_content")
    search_filename = data.get("search_filename")
    search_dir_rel = data.get("search_dir")

    # Resolve the search directory
    # Ensure we stay within /data for security
    target_dir = BASE_DATA_DIR
    if search_dir_rel:
        # Remove leading slash to join correctly and prevent absolute path escape
        rel_path = search_dir_rel.lstrip('/')
        target_dir = os.path.join(BASE_DATA_DIR, rel_path)

    # Validate that the target directory exists and is within /data
    if not os.path.exists(target_dir) or not os.path.isdir(target_dir):
        return web.json_response({"files": []}, status=200)
    
    if not os.path.abspath(target_dir).startswith(os.path.abspath(BASE_DATA_DIR)):
        return web.json_response({"error": "Invalid search directory"}, status=400)

    matching_files = []

    # We use run_in_executor for blocking I/O operations (os.walk, open)
    def perform_search():
        results = []
        for root, dirs, files in os.walk(target_dir):
            for file in files:
                full_path = os.path.join(root, file)
                
                # Check filename match
                name_match = False
                if search_filename and file.startswith(search_filename):
                    name_match = True
                
                # Check content match
                content_match = False
                if search_content:
                    try:
                        # Open in binary mode to avoid encoding crashes on non-text files
                        with open(full_path, 'rb') as f:
                            # Read in chunks to handle large files
                            content_bytes = search_content.encode('utf-8')
                            while True:
                                chunk = f.read(4096)
                                if not chunk:
                                    break
                                if content_bytes in chunk:
                                    content_match = True
                                    break
                    except (OSError, IOError):
                        pass # Skip files that cannot be read

                if name_match or content_match:
                    results.append(full_path)
        return results

    loop = asyncio.get_event_loop()
    files_found = await loop.run_in_executor(None, perform_search)
    
    return web.json_response({"files": files_found})

async def init_app():
    app = web.Application()
    app.add_routes([web.post('/search', search_files_handler)])
    return app

if __name__ == "__main__":
    app = asyncio.run(init_app()) # This is a placeholder, aiohttp.web.run_app is standard
    # Correct way to run aiohttp app
    web.run_app(app, host=HOST, port=PORT)