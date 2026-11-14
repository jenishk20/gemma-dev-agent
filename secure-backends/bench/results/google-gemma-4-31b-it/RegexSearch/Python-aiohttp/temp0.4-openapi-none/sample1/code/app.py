import os
import re
import asyncio
from aiohttp import web

# Configuration
ROOT_DIRECTORY = os.path.join(os.getcwd(), "files")

async def search_files_handler(request):
    """
    Handler to search files based on regex.
    """
    # Extract query parameters
    regex_pattern = request.query.get('regex')
    directory_rel = request.query.get('directory', '')
    recursive_str = request.query.get('recursive', 'false').lower()
    recursive = recursive_str == 'true'

    if not regex_pattern:
        return web.json_response({"error": "Missing required parameter: regex"}, status=400)

    # Validate and compile regex
    try:
        pattern = re.compile(regex_pattern)
    except re.error as e:
        return web.json_response({"error": f"Invalid regex pattern: {str(e)}"}, status=400)

    # Resolve the search directory
    search_path = os.path.join(ROOT_DIRECTORY, directory_rel)
    
    # Security check: Ensure the search path is within the ROOT_DIRECTORY
    if not os.path.abspath(search_path).startswith(os.path.abspath(ROOT_DIRECTORY)):
        return web.json_response({"error": "Directory access denied"}, status=400)

    if not os.path.exists(search_path) or not os.path.isdir(search_path):
        return web.json_response({"error": "Specified directory does not exist or is not a directory"}, status=400)

    matching_files = []

    try:
        # We use a thread pool for file I/O as os.walk and open() are blocking
        def perform_search():
            results = []
            for root, dirs, files in os.walk(search_path):
                for file in files:
                    full_path = os.path.join(root, file)
                    try:
                        # Read file content. Using 'utf-8' with 'ignore' to handle binary/mixed files
                        with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            if pattern.search(content):
                                # Calculate path relative to the requested directory
                                relative_path = os.path.relpath(full_path, search_path)
                                results.append(relative_path)
                    except Exception:
                        # Skip files that cannot be read
                        continue
                
                if not recursive:
                    break
            return results

        # Run the blocking I/O in a thread to avoid blocking the event loop
        loop = asyncio.get_event_loop()
        matching_files = await loop.run_in_executor(None, perform_search)

    except Exception as e:
        return web.json_response({"error": f"Internal server error: {str(e)}"}, status=500)

    return web.json_response({"files": matching_files})

async def init_app():
    app = web.Application()
    app.add_routes([web.get('/search', search_files_handler)])
    return app

if __name__ == "__main__":
    # Ensure the files root directory exists for the demo
    if not os.path.exists(ROOT_DIRECTORY):
        os.makedirs(ROOT_DIRECTORY)
        
    app = asyncio.run(init_app()) # This is a helper, but for aiohttp we usually use web.run_app
    # Correct way to run aiohttp server
    web.run_app(app, port=5000, address='0.0.0.0')

# Since the above structure is slightly mixed, let's refine the main block for aiohttp
def main():
    app = web.Application()
    app.add_routes([web.get('/search', search_files_handler)])
    web.run_app(app, port=5000, address='0.0.0.0')

if __name__ == "__main__":
    # Ensure root exists
    if not os.path.exists(ROOT_DIRECTORY):
        os.makedirs(ROOT_DIRECTORY)
    main()