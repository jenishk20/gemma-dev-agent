import os
import re
import asyncio
from aiohttp import web

# Configuration
ROOT_FILES_DIR = "./files"
PORT = 5000
HOST = "0.0.0.0"

async def search_files_handler(request):
    """
    Handler to search files based on a regex pattern.
    """
    # Extract query parameters
    regex_pattern = request.query.get('regex')
    directory_rel = request.query.get('directory', '')
    recursive_str = request.query.get('recursive', 'false').lower()
    recursive = recursive_str == 'true'

    if not regex_pattern:
        return web.json_response({"error": "Missing required parameter: regex"}, status=400)

    # Validate regex
    try:
        pattern = re.compile(regex_pattern)
    except re.error as e:
        return web.json_response({"error": f"Invalid regex pattern: {str(e)}"}, status=400)

    # Construct absolute search path
    # Ensure the directory is within the ROOT_FILES_DIR to prevent directory traversal
    search_path = os.path.abspath(os.path.join(ROOT_FILES_DIR, directory_rel))
    root_abs = os.path.abspath(ROOT_FILES_DIR)

    if not search_path.startswith(root_abs):
        return web.json_response({"error": "Directory path is outside the allowed root directory"}, status=400)

    if not os.path.exists(search_path) or not os.path.isdir(search_path):
        return web.json_response({"error": "Specified directory does not exist or is not a directory"}, status=400)

    matching_files = []

    try:
        # We use a thread pool for file I/O to avoid blocking the event loop
        def perform_search():
            results = []
            if recursive:
                for root, dirs, files in os.walk(search_path):
                    for file in files:
                        full_path = os.path.join(root, file)
                        try:
                            # Read file content. Using 'utf-8' with 'ignore' to handle binary/non-utf8 files gracefully
                            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                                content = f.read()
                                if pattern.search(content):
                                    # Calculate path relative to the requested directory
                                    rel_path = os.path.relpath(full_path, search_path)
                                    results.append(rel_path)
                        except Exception:
                            continue # Skip files that cannot be read
            else:
                for entry in os.scandir(search_path):
                    if entry.is_file():
                        try:
                            with open(entry.path, 'r', encoding='utf-8', errors='ignore') as f:
                                content = f.read()
                                if pattern.search(content):
                                    results.append(entry.name)
                        except Exception:
                            continue
            return results

        loop = asyncio.get_event_loop()
        matching_files = await loop.run_in_executor(None, perform_search)

    except Exception as e:
        return web.json_response({"error": f"Internal server error: {str(e)}"}, status=500)

    return web.json_response({"files": matching_files}, status=200)

async def init_app():
    app = web.Application()
    app.add_routes([web.get('/search', search_files_handler)])
    return app

if __name__ == "__main__":
    # Ensure root files directory exists for the demo
    if not os.path.exists(ROOT_FILES_DIR):
        os.makedirs(ROOT_FILES_DIR)
        
    app = asyncio.run(init_app()) # This is a helper, but for aiohttp we usually use web.run_app
    # Re-initializing properly for web.run_app
    async def start_server():
        app = web.Application()
        app.add_routes([web.get('/search', search_files_handler)])
        web.run_app(app, host=HOST, port=PORT)

    # To avoid nested loops in some environments, we call run_app directly
    app_instance = web.Application()
    app_instance.add_routes([web.get('/search', search_files_handler)])
    web.run_app(app_instance, host=HOST, port=PORT)