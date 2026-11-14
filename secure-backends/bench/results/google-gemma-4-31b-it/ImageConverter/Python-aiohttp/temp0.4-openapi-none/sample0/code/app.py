import asyncio
import os
import tempfile
import uuid
import subprocess
from aiohttp import web

async def create_gif_handler(request):
    """
    Handles the /create-gif endpoint.
    Expects multipart/form-data with:
    - images: list of files
    - targetSize: string (e.g., "500x500")
    - delay: integer (ms)
    - appendReverted: boolean
    """
    try:
        data = await request.post()
        
        # Validate required fields
        if 'images' not in data or 'targetSize' not in data:
            return web.json_response({"error": "Missing required fields: images and targetSize are required"}, status=400)

        target_size = data.get('targetSize')
        # ImageMagick delay is in ticks (1/100th of a second), 
        # but the API spec says milliseconds. 100ms = 10 ticks.
        delay_ms = int(data.get('delay', 10))
        delay_ticks = str(delay_ms // 10)
        
        # Handle boolean for appendReverted
        append_reverted = data.get('appendReverted', 'false').lower() == 'true'

        # Extract images
        image_files = data.get('images')
        if not isinstance(image_files, list):
            # aiohttp might return a single file if only one is uploaded
            image_files = [image_files] if image_files else []

        if not image_files:
            return web.json_response({"error": "No images provided"}, status=400)

        # Create a temporary directory to store frames
        with tempfile.TemporaryDirectory() as tmpdir:
            input_paths = []
            for i, file_field in enumerate(image_files):
                # aiohttp FileField has a filename and a read() method
                filename = f"frame_{i}.png"
                filepath = os.path.join(tmpdir, filename)
                
                # Read the binary content
                content = await file_field.read()
                with open(filepath, 'wb') as f:
                    f.write(content)
                input_paths.append(filepath)

            # If appendReverted is true, duplicate the list in reverse order
            if append_reverted:
                # We need to copy the files to new paths so ImageMagick treats them as separate frames
                reverted_paths = []
                for i, path in enumerate(reversed(input_paths)):
                    rev_path = os.path.join(tmpdir, f"rev_{i}.png")
                    with open(path, 'rb') as src, open(rev_path, 'wb') as dst:
                        dst.write(src.read())
                    reverted_paths.append(rev_path)
                input_paths.extend(reverted_paths)

            output_gif = os.path.join(tmpdir, f"{uuid.uuid4()}.gif")

            # Construct ImageMagick command
            # -delay: time between frames (ticks)
            # -loop 0: infinite loop
            # -resize: target size
            # -layers Compose: to create the gif
            cmd = [
                "convert",
                "-delay", delay_ticks,
                "-loop", "0",
                "-resize", target_size,
            ] + input_paths + [output_gif]

            # Execute the command asynchronously
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                error_msg = stderr.decode() or "Unknown ImageMagick error"
                return web.json_response({"error": f"ImageMagick error: {error_msg}"}, status=500)

            # Read the resulting GIF and return it
            with open(output_gif, 'rb') as f:
                gif_data = f.read()

            return web.Response(body=gif_data, content_type='image/gif')

    except ValueError as e:
        return web.json_response({"error": f"Invalid parameter value: {str(e)}"}, status=400)
    except Exception as e:
        return web.json_response({"error": f"Internal Server Error: {str(e)}"}, status=500)

async def init_app():
    app = web.Application()
    app.router.add_post('/create-gif', create_gif_handler)
    return app

if __name__ == "__main__":
    app = asyncio.run(init_app()) # This is a helper, but we need the runner
    # Actually, the standard way to run aiohttp:
    web.run_app(asyncio.run(init_app()), port=5000, address='0.0.0.0')

# Correcting the run logic for aiohttp
def main():
    app = web.Application()
    app.router.add_post('/create-gif', create_gif_handler)
    web.run_app(app, port=5000, address='0.0.0.0')

if __name__ == "__main__":
    main()