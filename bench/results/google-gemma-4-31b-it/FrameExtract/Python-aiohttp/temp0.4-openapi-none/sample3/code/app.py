import asyncio
import os
import tempfile
import subprocess
from aiohttp import web

async def extract_frame(request):
    """
    Handles the /extract endpoint to extract a specific frame from a video.
    """
    # Parse multipart form data
    data = await request.post()
    
    video_file = data.get('video')
    frame_number_str = data.get('frameNumber')
    
    if not video_file or not frame_number_str:
        return web.json_response({"error": "Missing video or frameNumber"}, status=400)

    try:
        frame_number = int(frame_number_str)
    except ValueError:
        return web.json_response({"error": "frameNumber must be an integer"}, status=400)

    # Create a temporary directory to handle the video and output image
    with tempfile.TemporaryDirectory() as tmpdir:
        # Save uploaded video to disk
        video_path = os.path.join(tmpdir, "input_video.mp4")
        with open(video_path, 'wb') as f:
            f.write(video_file.file.read())

        # Output path for the extracted frame
        output_path = os.path.join(tmpdir, "frame.png")

        # FFmpeg command to extract a specific frame
        # -i: input file
        # -vf "select=eq(n\,X)": filter to select frame X (0-indexed)
        # -vframes 1: output exactly one frame
        cmd = [
            'ffmpeg', 
            '-i', video_path, 
            '-vf', f'select=eq(n\\,{frame_number})', 
            '-vframes', '1', 
            '-f', 'image2', 
            output_path
        ]

        # Run ffmpeg asynchronously
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

        # Read the resulting image and return it
        with open(output_path, 'rb') as f:
            image_data = f.read()

        return web.Response(body=image_data, content_type='image/png')

async def init_app():
    app = web.Application()
    app.router.add_post('/extract', extract_frame)
    return app

if __name__ == '__main__':
    app = asyncio.run(init_app())
    web.run_app(app, host='0.0.0.0', port=5000)