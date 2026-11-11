import os
import re
import asyncio
from aiohttp import web

# Configuration
ROOT_FILES_DIR = os.path.join(os.getcwd(), "files")

async def search_files_handler(request):
    """
    Handler to search files based on a regex pattern.
    """
    # Extract query parameters
    regex_pattern = request.query.get('regex')
    directory_rel = request.query.get('directory', '')
    recursive = request.query.get('recursive', 'false').lower() == 'true'

    if not regex_pattern:
        return web.json_response({"error": "Missing required parameter: regex"}, status=400)

    # Validate and compile regex
    try:
        pattern = re.compile(regex_pattern)
    except re.error as e:
        return web.json_response({"error": f"Invalid regex pattern: {str(e)}"}, status=400)

    # Resolve the search directory
    # Ensure the directory is within the ROOT_FILES_DIR to prevent directory traversal attacks
    search_path = os.path.abspath(os.path.join(ROOT_FILES_DIR, directory_rel))
    if not search_path.startswith(os.path.abspath(ROOT_FILES_DIR)):
        return web.json_response({"error": "Invalid directory path: access denied"}, status=400)

    if not os.path.exists(search_path) or not os.path.isdir(search_path):
        return web.json_response({"error": "Directory not found or inaccessible"}, status=400)

    matching_files = []

    try:
        # We use a thread pool for file I/O since os.walk and open are blocking
        def perform_search():
            found = []
            if recursive:
                for root, dirs, files in os.walk(search_path):
                    for file in files:
                        full_path = os.path.join(root, file)
                        try:
                            # Read file content. Using 'utf-8' with 'ignore' to handle binary or mixed files
                            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                                content = f.read()
                                if pattern.search(content):
                                    # Calculate path relative to the requested directory
                                    rel_path = os.path.relpath(full_path, search_path)
                                    found.append(rel_path)
                        except Exception:
                            continue # Skip files that cannot be read
            else:
                # Non-recursive: only files in the immediate directory
                for entry in os.scandir(search_path):
                    if entry.is_file():
                        try:
                            with open(entry.path, 'r', encoding='utf-8', errors='ignore') as f:
                                content = f.read()
                                if pattern.search(content):
                                    found.append(entry.name)
                        except Exception:
                            continue
            return found

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
    # Ensure the root files directory exists for the demo
    if not os.path.exists(ROOT_FILES_DIR):
        os.makedirs(ROOT_FILES_DIR)
        
    app = asyncio.run(init_app()) # This is a helper, but we need to run the app
    # Since we need to start the server on 0.0.0.0:5000
    web.run_app(app, port=5000, address='0.0.0.0')

# Correcting the run logic to avoid asyncio.run conflict with web.run_app
def start_server():
    app = web.Application()
    app.add_routes([web.get('/search', search_files_handler)])
    web.run_app(app, port=5000, address='0.0.0.0')

if __name__ == "__main__":
    if not os.path.exists(ROOT_FILES_DIR):
        os.makedirs(ROOT_FILES_DIR)
    start_server()