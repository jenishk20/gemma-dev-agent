import asyncio
import os
import tempfile
import uuid
from aiohttp import web

async def extract_frame(handler):
    # Read multipart data
    reader = await handler.multipart()
    
    video_data = None
    video_filename = None
    frame_number = None

    while True:
        part = await reader.next()
        if part is None:
            break
        
        if part.name == 'video':
            video_filename = part.filename
            video_data = await part.read()
        elif part.name == 'frameNumber':
            # Multipart fields are usually bytes
            val = await part.read()
            frame_number = int(val.decode('utf-8'))
        elif part.name == 'videoFileName':
            val = await part.read()
            video_filename = val.decode('utf-8')

    if video_data is None or frame_number is None:
        return web.json_response({"error": "Missing required fields: video and frameNumber"}, status=400)

    # Create temporary directory for processing
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, f"input_{uuid.uuid4()}.mp4")
        output_path = os.path.join(tmpdir, f"output_{uuid.uuid4()}.png")

        with open(input_path, 'wb') as f:
            f.write(video_data)

        # ffmpeg command to extract a specific frame
        # -i: input file
        # -frames:v 1: output exactly one frame
        # -vf: video filter to select the frame index
        cmd = [
            'ffmpeg',
            '-i', input_path,
            '-vf', f'select=eq(n,{frame_number})',
            '-vframes', '1',
            '-f', 'image2',
            output_path
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0 or not os.path.exists(output_path):
            return web.json_response(
                {"error": f"Frame at index {frame_number} could not be found."}, 
                status=404
            )

        # Read the resulting image
        with open(output_path, 'rb') as f:
            image_bytes = f.read()

        return web.Response(body=image_bytes, content_type='image/png')

async def init_app():
    app = web.Application()
    app.router.add_post('/extract', extract_frame)
    return app

if __name__ == '__main__':
    app = asyncio.run(init_app()) # This is a conceptual wrapper, aiohttp.web.run_app is standard
    # Correct way to run aiohttp app:
    web.run_app(asyncio.run(init_app()), port=5000, address='0.0.0.0')
# Wait, the above logic in __main__ is slightly wrong for aiohttp. Let's fix it.