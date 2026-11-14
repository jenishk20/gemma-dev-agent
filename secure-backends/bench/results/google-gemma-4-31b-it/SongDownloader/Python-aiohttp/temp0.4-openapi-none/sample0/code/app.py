import os
from aiohttp import web

# Configuration
SONGS_DIRECTORY = "/var/songs"
HOST = "0.0.0.0"
PORT = 5000

async def handle_download(request):
    """
    Handles the POST /download endpoint.
    Expects JSON body: {"filename": "song.mp3"}
    """
    try:
        # Parse the JSON request body
        data = await request.json()
    except Exception:
        return web.Response(text="Invalid JSON input", status=400)

    if not data or 'filename' not in data:
        return web.Response(text="Missing 'filename' in request body", status=400)

    filename = data['filename']

    # Security: Prevent directory traversal attacks by normalizing the path 
    # and ensuring it stays within the SONGS_DIRECTORY
    # We strip leading slashes and ensure the resulting path is inside the target dir
    safe_filename = os.path.basename(filename)
    file_path = os.path.join(SONGS_DIRECTORY, safe_filename)

    # Check if file exists and is actually a file
    if not os.path.isfile(file_path):
        return web.Response(text="File does not exist", status=404)

    # Use a FileResponse to stream the content efficiently
    # aiohttp.web.FileResponse handles chunked reading and setting the correct content-length
    return web.FileResponse(file_path, content_type='audio/mpeg')

async def init_app():
    app = web.Application()
    app.add_routes([web.post('/download', handle_download)])
    return app

if __name__ == "__main__":
    # Ensure the directory exists for the sake of the server starting, 
    # though in production /var/songs would be pre-configured.
    if not os.path.exists(SONGS_DIRECTORY):
        try:
            os.makedirs(SONGS_DIRECTORY)
        except PermissionError:
            print(f"Warning: Could not create {SONGS_DIRECTORY}. Ensure the directory exists.")

    app = web.Application()
    app.add_routes([web.post('/download', handle_download)])
    
    print(f"Starting SongDownloader API on {HOST}:{PORT}...")
    web.run_app(app, host=HOST, port=PORT)