import os
import uuid
import mimetypes
from aiohttp import web

# Configuration
UPLOAD_DIR = "uploads"
PORT = 5000
HOST = "0.0.0.0"

# Ensure upload directory exists
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

async def upload_image(request):
    """
    Handles POST /upload
    Expects multipart/form-data with a field named 'file'
    """
    try:
        # Read the multipart data
        reader = await request.multipart()
        field = None
        
        while True:
            part = await reader.next()
            if part is None:
                break
            if part.name == 'file':
                field = part
                break
        
        if field is None:
            return web.json_response({"error": "No file uploaded under field 'file'"}, status=400)

        # Generate a unique ID and determine extension
        filename = field.filename
        if not filename:
            return web.json_response({"error": "Filename is missing"}, status=400)
            
        ext = os.path.splitext(filename)[1]
        image_id = str(uuid.uuid4())
        save_path = os.path.join(UPLOAD_DIR, f"{image_id}{ext}")

        # Save the file to disk
        with open(save_path, 'wb') as f:
            while True:
                chunk = await field.read_chunk()
                if not chunk:
                    break
                f.write(chunk)

        return web.json_response({"id": image_id}, status=200)

    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

async def get_image(request):
    """
    Handles GET /images/{imageId}
    Serves the image file with the correct mimetype to ensure browser viewing
    """
    image_id = request.match_info.get('imageId')
    
    # Search for the file in the upload directory that starts with the image_id
    try:
        target_file = None
        for file in os.listdir(UPLOAD_DIR):
            if file.startswith(image_id):
                target_file = os.path.join(UPLOAD_DIR, file)
                break
        
        if target_file is None or not os.path.exists(target_file):
            return web.json_response({"error": "Image not found"}, status=404)

        # Determine mimetype
        mime_type, _ = mimetypes.guess_type(target_file)
        if not mime_type:
            mime_type = 'application/octet-stream'

        # To prevent download and encourage browser viewing, we set Content-Type 
        # and ensure Content-Disposition is not 'attachment'.
        # aiohttp.web.FileResponse handles the streaming and mime-type.
        return web.FileResponse(target_file, content_type=mime_type)

    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

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