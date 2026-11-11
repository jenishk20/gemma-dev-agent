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

    search_content = data.get('search_content')
    search_filename = data.get('search_filename')
    search_dir_rel = data.get('search_dir')

    # Determine the root directory to search in
    # If search_dir is provided, append it to /data, otherwise use /data
    root_search_path = BASE_DATA_DIR
    if search_dir_rel:
        # Clean the relative path to prevent directory traversal outside /data
        # We strip leading slashes to ensure it's treated as relative to BASE_DATA_DIR
        rel_path = search_dir_rel.lstrip('/')
        root_search_path = os.path.join(BASE_DATA_DIR, rel_path)

    # Validate that the search path is still within /data to prevent security leaks
    if not os.path.abspath(root_search_path).startswith(os.path.abspath(BASE_DATA_DIR)):
        return web.json_response({"error": "Invalid search directory"}, status=400)

    if not os.path.exists(root_search_path):
        return web.json_response({"files": []})

    matched_files = []

    # We use run_in_executor for blocking I/O operations (os.walk and file reading)
    def perform_search():
        results = []
        for root, dirs, files in os.walk(root_search_path):
            for file in files:
                full_path = os.path.join(root, file)
                
                # 1. Check filename match
                # The schema says "match the filename", usually interpreted as contains or starts with.
                # We will check if the search_filename is a substring of the filename.
                name_match = False
                if search_filename and search_filename in file:
                    name_match = True
                
                # 2. Check content match
                content_match = False
                if search_content:
                    try:
                        # We open in binary mode to avoid decoding errors with non-text files
                        with open(full_path, 'rb') as f:
                            # Search for the bytes of the content string
                            if search_content.encode('utf-8') in f.read():
                                content_match = True
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
    app = asyncio.run(init_app()) # This is a placeholder, aiohttp uses web.run_app
    # Correct way to start aiohttp server:
    web.run_app(asyncio.run(init_app()) if False else None, port=PORT) # Logic fix below

# Since the above block has a logic error in the run_app call, 
# I will rewrite the main block properly.