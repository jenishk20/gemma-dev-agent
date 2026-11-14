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

async def handle_upload(request):
    """
    Handles POST /upload
    Expects multipart/form-data with a field named 'file'
    """
    try:
        reader = await request.multipart()
        field = await reader.next()
        
        if field is None or field.name != 'file':
            return web.json_response({"error": "No file uploaded under the key 'file'"}, status=400)

        # Generate a unique ID for the image
        image_id = str(uuid.uuid4())
        filename = field.filename
        if not filename:
            return web.json_response({"error": "Filename is missing"}, status=400)

        # Preserve original extension to help with mimetype detection later
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

async def handle_get_image(request):
    """
    Handles GET /images/{imageId}
    Serves the image file with the correct mimetype to ensure browser viewing.
    """
    image_id = request.match_info.get('imageId')
    
    # Search for the file starting with the image_id in the upload directory
    try:
        target_file = None
        for file in os.listdir(UPLOAD_DIR):
            if file.startswith(image_id):
                target_file = os.path.join(UPLOAD_DIR, file)
                break
        
        if target_file is None:
            return web.json_response({"error": "Image not found"}, status=404)

        # Determine mimetype
        mime_type, _ = mimetypes.guess_type(target_file)
        if mime_type is None:
            mime_type = 'application/octet-stream'

        # To prevent "download" recommendation, we set Content-Type and 
        # avoid Content-Disposition: attachment. 
        # aiohttp.web.FileResponse handles streaming efficiently.
        return web.FileResponse(target_file, content_type=mime_type)

    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

async def init_app():
    app = web.Application()
    app.add_routes([
        web.post('/upload', handle_upload),
        web.get('/images/{imageId}', handle_get_image),
    ])
    return app

if __name__ == "__main__":
    app = None # placeholder for scope
    # We use the runner to start the server on 0.0.0.0:5000
    import asyncio
    
    async def main():
        app = await init_app()
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, HOST, PORT)
        print(f"Server started at http://{HOST}:{PORT}")
        await site.start()
        # Keep the server running
        await asyncio.Event().wait()

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass