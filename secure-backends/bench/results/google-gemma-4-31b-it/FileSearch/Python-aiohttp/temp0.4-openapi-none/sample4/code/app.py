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
    base_search_path = DATA_ROOT
    if search_dir_rel:
        # Basic sanitization to prevent directory traversal above /data
        normalized_rel = os.path.normpath(search_dir_rel).lstrip(os.sep).lstrip('/')
        base_search_path = os.path.join(DATA_ROOT, normalized_rel)

    if not os.path.exists(base_search_path) or not os.path.isdir(base_search_path):
        return web.json_response({"files": []}, status=200)

    found_files = []

    # We use run_in_executor for blocking I/O operations (os.walk, open)
    def perform_search():
        results = []
        for root, dirs, files in os.walk(base_search_path):
            for file in files:
                full_path = os.path.join(root, file)
                
                # Check filename match
                # The schema says "match the filename" or "start", usually interpreted as contains or starts with
                if search_filename and search_filename not in file:
                    continue
                
                # Check content match
                if search_content:
                    try:
                        # We open in binary mode to avoid encoding crashes on non-text files
                        with open(full_path, 'rb') as f:
                            content = f.read()
                            if search_content.encode('utf-8') not in content:
                                continue
                    except (OSError, IOError):
                        continue
                
                results.append(full_path)
        return results

    loop = asyncio.get_event_loop()
    files_list = await loop.run_in_executor(None, perform_search)
    
    return web.json_response({"files": files_list})

async def init_app():
    app = web.Application()
    app.add_routes([web.post('/search', search_files_handler)])
    return app

if __name__ == "__main__":
    app = asyncio.run(init_app()) # This is a placeholder logic, aiohttp uses web.run_app
    # Correct way to run aiohttp app:
    async def start_server():
        app = await init_app()
        web.run_app(app, host=HOST, port=PORT)

    # Since web.run_app is blocking, we call it directly
    app_instance = None
    async def setup():
        global app_instance
        app_instance = await init_app()
    
    # Standard aiohttp entry point
    async def run():
        app = await init_app()
        # Note: run_app is a blocking call that handles the loop
        # To keep it in one file and runnable:
        web.run_app(app, host=HOST, port=PORT)

    # To avoid nested loops in some environments, we use the standard aiohttp pattern
    # but since we need to call init_app (async), we do:
    import asyncio
    
    async def main():
        app = await init_app()
        # We can't call run_app inside an existing loop easily, 
        # so we use the standard approach:
        # But run_app creates its own loop.
        pass

    # Correct implementation for aiohttp standalone
    def start():
        # We wrap the async init in a synchronous way for run_app
        # However, aiohttp's run_app expects an Application object.
        # Since init_app is async, we run it first.
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        app = loop.run_until_complete(init_app())
        web.run_app(app, host=HOST, port=PORT)

    start()