import asyncio
import os
import tempfile
import shutil
from aiohttp import web

async def create_gif_handler(request):
    """
    Handles the /create-gif endpoint.
    Expects multipart/form-data with images, targetSize, delay, and appendReverted.
    """
    try:
        # Parse multipart data
        data = await request.post()
        
        # Extract fields
        target_size = data.get('targetSize')
        delay_val = data.get('delay', '10')
        append_reverted = data.get('appendReverted', 'false').lower() == 'true'
        
        # Extract images
        # aiohttp stores uploaded files in data['images'] if it's a single file, 
        # but for multiple files with the same name, we need to handle the FileStorage objects.
        images = []
        # The OpenAPI schema says 'images' is an array. In multipart, 
        # multiple files with the same key are usually handled by iterating the fields.
        # We look for all fields named 'images'.
        for field in request.post():
            if field.name == 'images':
                # Read the binary content of the uploaded file
                content = await field.read()
                images.append(content)

        if not images:
            return web.json_response({'error': 'No images provided'}, status=400)
        
        if not target_size:
            return web.json_response({'error': 'targetSize is required'}, status=400)

        # Validate targetSize format (e.g., 500x500)
        if 'x' not in target_size:
            return web.json_response({'error': 'targetSize must be in format WxH'}, status=400)

        # Create a temporary directory to store frames
        with tempfile.TemporaryDirectory() as tmpdir:
            frame_paths = []
            for i, img_bytes in enumerate(images):
                path = os.path.join(tmpdir, f"frame_{i}.png")
                with open(path, 'wb') as f:
                    f.write(img_bytes)
                frame_paths.append(path)

            # If appendReverted is true, add the images in reverse order
            if append_reverted:
                for i, img_bytes in enumerate(reversed(images)):
                    path = os.path.join(tmpdir, f"rev_{i}.png")
                    with open(path, 'wb') as f:
                        f.write(img_bytes)
                    frame_paths.append(path)

            # Construct ImageMagick command
            # -delay is in hundredths of a second. 
            # The API says delay is in milliseconds. 100ms = 10 ticks.
            try:
                delay_ms = int(delay_val)
                im_delay = str(delay_ms // 10)
            except ValueError:
                im_delay = "1"

            output_gif = os.path.join(tmpdir, "output.gif")
            
            # Command: convert -delay X -loop 0 -resize WxH frame1 frame2 ... output.gif
            # Note: -resize is used to match targetSize
            cmd = [
                "convert",
                "-delay", im_delay,
                "-loop", "0",
                "-resize", target_size,
            ] + frame_paths + [output_gif]

            # Run the conversion process
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                return web.json_response({'error': f"ImageMagick error: {stderr.decode()}"}, status=500)

            # Read the resulting GIF
            with open(output_gif, 'rb') as f:
                gif_data = f.read()

            return web.Response(body=gif_data, content_type='image/gif')

    except Exception as e:
        return web.json_response({'error': str(e)}, status=500)

async def init_app():
    app = web.Application()
    app.add_routes([web.post('/create-gif', create_gif_handler)])
    return app

if __name__ == '__main__':
    app = asyncio.run(init_app()) # This is not how aiohttp runs, corrected below
    
# Correcting the runner for aiohttp
if __name__ == '__main__':
    app = web.Application()
    app.add_routes([web.post('/create-gif', create_gif_handler)])
    web.run_app(app, host='0.0.0.0', port=5000)