import asyncio
import os
import tempfile
import uuid
import subprocess
from aiohttp import web

async def create_gif_handler(request):
    """
    Handler to create a GIF from uploaded images using ImageMagick.
    """
    try:
        data = await request.post()
        
        # Extract required fields
        images = data.get('images')
        target_size = data.get('targetSize')
        delay_str = data.get('delay', '10')
        append_reverted_str = data.get('appendReverted', 'false')

        if not images or not target_size:
            return web.json_response({"error": "Missing required fields: images and targetSize"}, status=400)

        # Handle boolean conversion for appendReverted
        append_reverted = append_reverted_str.lower() == 'true'
        
        # Validate delay is an integer
        try:
            delay = int(delay_str)
        except ValueError:
            return web.json_response({"error": "delay must be an integer"}, status=400)

        # Create a temporary directory to store uploaded frames
        with tempfile.TemporaryDirectory() as tmpdir:
            input_files = []
            
            # Process uploaded files
            # aiohttp multipart data.get('images') returns a list of FileReader objects
            for i, file_field in enumerate(images):
                file_path = os.path.join(tmpdir, f"frame_{i}.img")
                with open(file_path, 'wb') as f:
                    while True:
                        chunk = await file_field.read(8192)
                        if not chunk:
                            break
                        f.write(chunk)
                input_files.append(file_path)

            if not input_files:
                return web.json_response({"error": "No images provided"}, status=400)

            # If appendReverted is true, duplicate the list in reverse order
            if append_reverted:
                # We need to create copies of the files or just refer to them in the command
                # ImageMagick allows repeating filenames in the command line
                frames_list = input_files + input_files[::-1]
            else:
                frames_list = input_files

            output_gif_path = os.path.join(tmpdir, "result.gif")
            
            # ImageMagick 'convert' command:
            # -delay: time between frames in ticks (1/100th of a second)
            # -resize: target size (e.g., 500x500)
            # -loop 0: infinite loop
            
            # Convert ms to ImageMagick ticks (1 tick = 10ms)
            im_delay = delay // 10
            
            cmd = [
                "convert",
                "-delay", str(im_delay),
                "-resize", target_size,
                "-loop", "0"
            ] + frames_list + [output_gif_path]

            # Run the conversion in a thread pool to avoid blocking the event loop
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                error_msg = stderr.decode() or "Unknown ImageMagick error"
                return web.json_response({"error": f"ImageMagick conversion failed: {error_msg}"}, status=500)

            # Read the resulting GIF and return it
            with open(output_gif_path, 'rb') as f:
                gif_data = f.read()

            return web.Response(body=gif_data, content_type='image/gif')

    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

async def init_app():
    app = web.Application()
    app.add_routes([web.post('/create-gif', create_gif_handler)])
    return app

if __name__ == '__main__':
    app = asyncio.run(init_app()) # This is a simplification, use web.run_app
    # Since we need to start the server on 0.0.0.0:5000
    web.run_app(app, port=5000, address='0.0.0.0')

# Correcting the entry point for aiohttp
def main():
    app = web.Application()
    app.add_routes([web.post('/create-gif', create_gif_handler)])
    web.run_app(app, port=5000, address='0.0.0.0')

if __name__ == '__main__':
    main()