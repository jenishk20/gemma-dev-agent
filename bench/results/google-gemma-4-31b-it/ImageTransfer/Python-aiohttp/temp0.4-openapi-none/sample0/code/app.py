import os
import uuid
import mimetypes
from aiohttp import web

# Configuration
UPLOAD_DIR = "uploaded_images"
PORT = 5000
HOST = "0.0.0.0"

# Ensure upload directory exists
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

async def upload_image(request):
    """
    Handles POST /upload
    Accepts multipart/form-data with a 'file' field.
    """
    try:
        reader = await request.multipart()
        field = await reader.next()
        
        if field is None or field.name != 'file':
            return web.json_response({"error": "No file uploaded under key 'file'"}, status=400)

        filename = field.filename
        if not filename:
            return web.json_response({"error": "File has no filename"}, status=400)

        # Generate a unique ID for the image to prevent collisions and directory traversal
        image_id = str(uuid.uuid4())
        
        # Determine extension from original filename
        ext = os.path.splitext(filename)[1]
        save_path = os.path.join(UPLOAD_DIR, f"{image_id}{ext}")

        # Save the file
        with open(save_path, 'wb') as f:
            while True:
                chunk = await field.read_chunk()
                if not chunk:
                    break
                f.write(chunk)

        return web.json_response({"id": image_id}, status=200)

    except Exception as e:
        print(f"Upload error: {e}")
        return web.json_response({"error": "Internal server error"}, status=500)

async def get_image(request):
    """
    Handles GET /images/{imageId}
    Serves the image with the correct mimetype to ensure browser viewing.
    """
    image_id = request.match_info.get('imageId')
    
    # Search for the file matching the ID in the upload directory
    target_file = None
    for filename in os.listdir(UPLOAD_DIR):
        if filename.startswith(image_id):
            target_file = os.path.join(UPLOAD_DIR, filename)
            break

    if target_file is None or not os.path.exists(target_file):
        return web.json_response({"error": "Image not found"}, status=404)

    try:
        # Determine mimetype for the browser
        mime_type, _ = mimetypes.guess_type(target_file)
        if not mime_type:
            mime_type = 'application/octet-stream'

        # Use FileResponse to stream the file. 
        # By default, aiohttp's FileResponse uses the mimetype and 
        # doesn't set Content-Disposition to 'attachment', 
        # which allows the browser to render it inline.
        return web.FileResponse(target_file, content_type=mime_type)
    except Exception as e:
        print(f"Retrieval error: {e}")
        return web.json_response({"error": "Internal server error"}, status=500)

async def init_app():
    app = web.Application()
    app.add_routes([
        web.post('/upload', upload_image),
        web.get('/images/{imageId}', get_image),
    ])
    return app

if __name__ == '__main__':
    app = web.Application()
    app.add_routes([
        web.post('/upload', upload_image),
        web.get('/images/{imageId}', get_image),
    ])
    web.run_app(app, host=HOST, port=PORT)