import os
import asyncio
from aiohttp import web

# Configuration
DATA_ROOT = "/data"
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

    # Determine the base directory to search in
    # If search_dir is provided, it's relative to /data
    base_dir = DATA_ROOT
    if search_dir_rel:
        # Normalize path to prevent directory traversal attacks
        # Ensure the resulting path is still within DATA_ROOT
        normalized_rel = os.path.normpath(search_dir_rel).lstrip('/')
        base_dir = os.path.join(DATA_ROOT, normalized_rel)
        if not base_dir.startswith(DATA_ROOT):
            return web.json_response({"error": "Invalid search directory"}, status=400)

    if not os.path.exists(base_dir) or not os.path.isdir(base_dir):
        return web.json_response({"files": []})

    matched_files = []

    # We use a thread pool for file system operations as they are blocking
    def perform_search():
        results = []
        for root, dirs, files in os.walk(base_dir):
            for file in files:
                full_path = os.path.join(root, file)
                
                # Check filename match (starts with)
                if search_filename and not file.startswith(search_filename):
                    # If filename is specified, it must match to proceed
                    # unless search_content is also provided and we want OR logic.
                    # The schema says "contain specified content OR match filename".
                    # However, usually, if both are provided, it's an AND or a union.
                    # We will treat them as: if filename matches, it's a hit. 
                    # If filename doesn't match, it can still be a hit if content matches.
                    pass 
                elif search_filename:
                    results.append(full_path)
                    continue

                # Check content match
                if search_content:
                    try:
                        # Open file and check if content exists in it
                        # Using 'rb' and encoding to handle potential binary files safely
                        with open(full_path, 'r', errors='ignore') as f:
                            if search_content in f.read():
                                results.append(full_path)
                    except Exception:
                        pass
                elif not search_filename:
                    # If neither is specified, we don't just return everything
                    pass
                elif search_filename and file.startswith(search_filename):
                    # Already added by the filename check above
                    pass
        
        # Remove duplicates and ensure paths are absolute/consistent
        return list(set(results))

    # Run blocking I/O in a thread
    loop = asyncio.get_event_loop()
    matched_files = await loop.run_in_executor(None, perform_search)

    return web.json_response({"files": matched_files})

async def init_app():
    app = web.Application()
    app.add_routes([web.post('/search', search_files_handler)])
    return app

if __name__ == "__main__":
    app = asyncio.run(init_app()) # This is a placeholder for the logic below
    # Correct way to start aiohttp server:
    app = web.Application()
    app.add_routes([web.post('/search', search_files_handler)])
    web.run_app(app, host=HOST, port=PORT)