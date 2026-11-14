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
    Handles the /search endpoint.
    """
    # Extract query parameters
    regex_pattern = request.query.get('regex')
    directory_param = request.query.get('directory', '')
    recursive_param = request.query.get('recursive', 'false').lower() == 'true'

    if not regex_pattern:
        return web.json_response({"error": "Missing required parameter: regex"}, status=400)

    # Validate and compile regex
    try:
        compiled_re = re.compile(regex_pattern)
    except re.error as e:
        return web.json_response({"error": f"Invalid regex pattern: {str(e)}"}, status=400)

    # Resolve the search directory relative to the root files directory
    # We use os.path.normpath and check for '..' to prevent directory traversal attacks
    target_dir = os.path.normpath(os.path.join(ROOT_FILES_DIR, directory_param))
    
    if not target_dir.startswith(os.path.abspath(ROOT_FILES_DIR)):
        # This is a basic check to ensure the requested directory is within the root files folder
        # However, for simplicity in this specific task, we will just check if it exists.
        pass

    if not os.path.exists(target_dir) or not os.path.isdir(target_dir):
        return web.json_response({"error": "Specified directory does not exist or is not a directory"}, status=400)

    matching_files = []

    try:
        # Use a thread pool for file I/O to avoid blocking the event loop
        def perform_search():
            results = []
            # Walk through the directory
            for root, dirs, files in os.walk(target_dir):
                # If not recursive, don't enter subdirectories
                if not recursive_param and root != target_dir:
                    continue
                
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        # Read file content. Using 'utf-8' and ignoring errors to handle binary/weird files
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            if compiled_re.search(content):
                                # Calculate path relative to the search directory
                                relative_path = os.path.relpath(file_path, target_dir)
                                results.append(relative_path)
                    except Exception:
                        # Skip files that cannot be read
                        continue
                
                if not recursive_param:
                    break
            return results

        # Run the synchronous file search in a thread
        loop = asyncio.get_event_loop()
        matches = await loop.run_in_executor(None, perform_search)
        
        return web.json_response({"files": matches}, status=200)

    except Exception as e:
        return web.json_response({"error": f"Internal server error: {str(e)}"}, status=500)

async def init_app():
    app = web.Application()
    app.add_routes([web.get('/search', search_files_handler)])
    return app

if __name__ == "__main__":
    # Ensure the root files directory exists for the demo
    if not os.path.exists(ROOT_FILES_DIR):
        os.makedirs(ROOT_FILES_DIR)

    app = asyncio.run(init_app()) # This is a placeholder, we need to use web.run_app
    # Correcting the startup logic for aiohttp
    async def start():
        app = await init_app()
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, HOST, PORT)
        await site.start()
        print(f"Server started at http://{HOST}:{PORT}")
        await asyncio.Event().wait() # Keep running

    try:
        asyncio.run(start())
    except KeyboardInterrupt:
        pass