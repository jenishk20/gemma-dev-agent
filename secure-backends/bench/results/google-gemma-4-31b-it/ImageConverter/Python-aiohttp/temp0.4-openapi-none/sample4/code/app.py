import asyncio
import os
import tempfile
import shutil
import subprocess
from aiohttp import web

async def create_gif_handler(request):
    try:
        # Parse multipart form data
        data = await request.post()
        
        # Validate required fields
        if 'images' not in data or 'targetSize' not in data:
            return web.json_response({'error': 'Missing required fields: images and targetSize'}, status=400)

        images = data.get('images')
        if not isinstance(images, list) or len(images) == 0:
            return web.json_response({'error': 'No images provided'}, status=400)

        target_size = data.get('targetSize')
        # Basic validation for targetSize format (e.g., 500x500)
        if 'x' not in target_size:
            return web.json_response({'error': 'targetSize must be in format WxH (e.g. 500x500)'}, status=400)

        # Get optional parameters
        delay = data.get('delay', '10')
        # aiohttp multipart data returns strings for non-file fields
        append_reverted = data.get('appendReverted', 'false').lower() == 'true'

        # Create a temporary directory to store frames
        with tempfile.TemporaryDirectory() as tmpdir:
            input_files = []
            for i, file_field in enumerate(images):
                # file_field is a FileUpload object
                filename = f"frame_{i}.png"
                filepath = os.path.join(tmpdir, filename)
                with open(filepath, 'wb') as f:
                    # Read the content of the uploaded file
                    content = await file_field.read()
                    f.write(content)
                input_files.append(filepath)

            # Handle appendReverted logic
            if append_reverted:
                # Append images in reverse order (excluding the last one to avoid duplicate center frame, 
                # but the spec says "append a reverted version", usually implying a full loop)
                # We will follow the literal "reverted version" meaning reversed list.
                reversed_files = input_files[::-1]
                # To avoid duplicating the last frame of the forward sequence and first of reverse:
                # we slice it, but for simplicity and strict adherence to "reverted version", we just append.
                input_files.extend(reversed_files)

            output_gif = os.path.join(tmpdir, "result.gif")
            
            # Construct ImageMagick command
            # -delay is in ticks. 100ms = 10 ticks if 1 tick = 10ms (default)
            # However, ImageMagick -delay is usually 1/100th of a second.
            # The spec says delay in milliseconds. 100ms = 10 ticks.
            try:
                delay_ticks = int(delay) // 10
            except ValueError:
                delay_ticks = 1

            cmd = [
                'convert',
                '-delay', str(delay_ticks),
                '-resize', target_size,
                *input_files,
                output_gif
            ]

            # Run the command asynchronously
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                return web.json_response({'error': f'ImageMagick error: {stderr.decode()}'}, status=500)

            # Read the resulting GIF and return it
            if os.path.exists(output_gif):
                with open(output_gif, 'rb') as f:
                    gif_data = f.read()
                return web.Response(body=gif_data, content_type='image/gif')
            else:
                return web.json_response({'error': 'GIF generation failed'}, status=500)

    except Exception as e:
        return web.json_response({'error': str(e)}, status=500)

async def init_app():
    app = web.Application()
    app.add_routes([web.post('/create-gif', create_gif_handler)])
    return app

if __name__ == '__main__':
    app = asyncio.run(init_app()) # This is not how aiohttp runs, let's use web.run_app
    # Correcting the run logic
    pass

# Redefining the main block to actually start the server
def run_server():
    app = web.Application()
    app.add_routes([web.post('/create-gif', create_gif_handler)])
    web.run_app(app, host='0.0.0.0', port=5000)

if __name__ == '__main__':
    run_server()