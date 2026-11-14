import asyncio
import os
import tempfile
import uuid
from aiohttp import web

async def create_gif_handler(request):
    """
    Handler to create a GIF based on the provided OpenAPI schema.
    """
    try:
        # Parse multipart form data
        data = await request.post()
        
        # Validate required fields
        images_files = data.get('images')
        target_size = data.get('targetSize')
        
        if not images_files or not target_size:
            return web.json_response({'error': 'Missing required fields: images and targetSize'}, status=400)

        # Handle images (aiohttp provides them as a list of FileStorage objects if multiple are uploaded)
        # Since the schema says 'array of images', we handle both single and multiple uploads
        if not isinstance(images_files, list):
            images_files = [images_files]

        if not images_files:
            return web.json_response({'error': 'No images provided'}, status=400)

        # Extract other parameters
        delay = data.get('delay', '10')
        append_reverted = data.get('appendReverted', 'false').lower() == 'true'

        # Create a temporary directory to store frames
        with tempfile.TemporaryDirectory() as tmpdir:
            input_paths = []
            for i, file_storage in enumerate(images_files):
                file_ext = os.path.splitext(file_storage.filename)[1] or '.img'
                file_path = os.path.join(tmpdir, f"frame_{i}{file_ext}")
                
                # Read content and write to disk
                content = await file_storage.read()
                with open(file_path, 'wb') as f:
                    f.write(content)
                input_paths.append(file_path)

            # Prepare ImageMagick command
            # -delay is in hundredths of a second in ImageMagick, but schema says milliseconds.
            # 100ms = 10 units in ImageMagick.
            try:
                im_delay = int(delay) // 10
            except ValueError:
                im_delay = 1

            # If appendReverted is true, duplicate the list in reverse order
            if append_reverted:
                input_paths = input_paths + input_paths[::-1]

            output_gif = os.path.join(tmpdir, "result.gif")
            
            # Construct the convert command
            # -resize targetSize (e.g., 500x500)
            # -delay im_delay
            # -loop 0 (infinite loop)
            cmd = [
                'convert',
                '-delay', str(im_delay),
                '-resize', target_size,
                '-loop', '0'
            ] + input_paths + [output_gif]

            # Execute the command asynchronously
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                error_msg = stderr.decode().strip() or "ImageMagick conversion failed"
                return web.json_response({'error': f'Conversion error: {error_msg}'}, status=500)

            # Return the resulting GIF file
            return web.FileResponse(output_gif, content_type='image/gif')

    except Exception as e:
        return web.json_response({'error': str(e)}, status=500)

async def init_app():
    app = web.Application()
    app.add_routes([web.post('/create-gif', create_gif_handler)])
    return app

if __name__ == '__main__':
    app = asyncio.run(init_app()) # This is not how you run aiohttp, using web.run_app
    # Correcting the run logic:
    async def start():
        app = web.Application()
        app.add_routes([web.post('/create-gif', create_gif_handler)])
        # We use a runner to ensure it binds to 0.0.0.0:5000
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', 5000)
        await site.start()
        print("Server started at http://0.0.0.0:5000")
        while True:
            await asyncio.sleep(3600)

    try:
        asyncio.run(start())
    except KeyboardInterrupt:
        pass