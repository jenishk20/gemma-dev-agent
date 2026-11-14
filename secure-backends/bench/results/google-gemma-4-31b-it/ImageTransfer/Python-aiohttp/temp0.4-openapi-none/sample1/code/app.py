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
    Expects multipart/form-data with a field named 'file'
    """
    try:
        reader = await request.multipart()
        field = await reader.next()
        
        if field is None or field.name != 'file':
            return web.json_response({"error": "No file field provided"}, status=400)

        filename = field.filename
        if not filename:
            return web.json_response({"error": "Empty filename"}, status=400)

        # Generate a unique ID to prevent collisions and directory traversal
        image_id = str(uuid.uuid4())
        
        # Determine extension based on original filename
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
        return web.json_response({"error": str(e)}, status=500)

async def get_image(request):
    """
    Handles GET /images/{imageId}
    Serves the image file with the correct mimetype and inline disposition.
    """
    image_id = request.match_info.get('imageId')
    
    # Find the file in the upload directory that starts with the image_id
    try:
        files = os.listdir(UPLOAD_DIR)
        target_file = next((f for f in files if f.startswith(image_id)), None)
        
        if target_file is None:
            return web.json_response({"error": "Image not found"}, status=404)

        file_path = os.path.join(UPLOAD_DIR, target_file)
        
        # Guess the mimetype based on the file extension
        mime_type, _ = mimetypes.guess_type(file_path)
        if not mime_type:
            mime_type = 'application/octet-stream'

        # 'inline' tells the browser to try and render it rather than download it
        return web.FileResponse(file_path, content_type=mime_type, content_disposition='inline')

    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

def main():
    app = web.Application()
    
    # Routes
    app.add_routes([
        web.post('/upload', upload_image),
        web.get('/images/{imageId}', get_image),
    ])
    
    print(f"Starting server on {HOST}:{PORT}...")
    web.run_app(app, host=HOST, port=PORT)

if __name__ == "__main__":
    main()