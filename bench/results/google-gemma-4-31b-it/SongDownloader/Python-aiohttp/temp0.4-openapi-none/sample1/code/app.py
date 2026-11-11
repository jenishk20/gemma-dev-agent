import os
from aiohttp import web

# Configuration
SONGS_DIRECTORY = "/var/songs"
HOST = "0.0.0.0"
PORT = 5000

async def download_song(request):
    """
    Handler to stream a song based on the filename provided in the JSON request body.
    """
    try:
        # Parse JSON body
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid input"}, status=400)

    if not data or 'filename' not in data:
        return web.json_response({"error": "Missing filename in request body"}, status=400)

    filename = data['filename']

    # Security: Prevent directory traversal attacks by ensuring the filename 
    # does not contain path separators and is just a base name.
    safe_filename = os.path.basename(filename)
    file_path = os.path.join(SONGS_DIRECTORY, safe_filename)

    # Check if file exists and is actually a file
    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        return web.Response(status=404, text="File does not exist")

    # Use FileResponse for efficient streaming of the file content
    # This handles chunking and content-length automatically
    return web.FileResponse(file_path, content_type='audio/mpeg')

async def init_app():
    app = web.Application()
    app.add_routes([web.post('/download', download_song)])
    return app

if __name__ == "__main__":
    app = web.Application()
    app.add_routes([web.post('/download', download_song)])
    
    print(f"Starting server on {HOST}:{PORT}...")
    web.run_app(app, host=HOST, port=PORT)