import os
import re
import asyncio
from aiohttp import web

# Configuration
ROOT_DIR = os.path.abspath("./files")

async def search_files_handler(request):
    """
    Handler for the /search endpoint.
    Searches files based on a regex pattern.
    """
    # Extract query parameters
    regex_pattern = request.query.get('regex')
    directory_param = request.query.get('directory', '')
    recursive_param = request.query.get('recursive', 'false').lower() == 'true'

    if not regex_pattern:
        return web.json_response({"error": "Missing required parameter: regex"}, status=400)

    # Validate and compile regex
    try:
        pattern = re.compile(regex_pattern)
    except re.error as e:
        return web.json_response({"error": f"Invalid regex pattern: {str(e)}"}, status=400)

    # Construct the absolute path to search
    # Ensure the directory parameter doesn't allow escaping the root files directory
    search_path = os.path.abspath(os.path.join(ROOT_DIR, directory_param))
    if not search_path.startswith(ROOT_DIR):
        return web.json_response({"error": "Directory access denied: path is outside root directory"}, status=400)

    if not os.path.exists(search_path):
        return web.json_response({"error": "Specified directory does not exist"}, status=400)
    
    if not os.path.isdir(search_path):
        return web.json_response({"error": "Specified path is not a directory"}, status=400)

    matching_files = []

    try:
        # We use a thread pool for file I/O to avoid blocking the event loop
        def perform_search():
            results = []
            if recursive_param:
                for root, dirs, files in os.walk(search_path):
                    for file in files:
                        full_path = os.path.join(root, file)
                        try:
                            # Read file content. Using 'utf-8' with 'ignore' to handle binary files gracefully
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

if __name__ == '__main__':
    # Ensure the root directory exists so the server doesn't crash on startup
    if not os.path.exists(ROOT_DIR):
        os.makedirs(ROOT_DIR)
        
    web.run_app(init_app(), port=5000, address='0.0.0.0')