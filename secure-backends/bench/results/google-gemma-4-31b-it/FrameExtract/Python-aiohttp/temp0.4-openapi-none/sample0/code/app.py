import asyncio
import os
import tempfile
import subprocess
from aiohttp import web

async def extract_frame(handler, request):
    """
    Handles the /extract endpoint.
    Expects multipart/form-data with 'video', 'frameNumber', and 'videoFileName'.
    """
    data = await request.post()
    
    # Validate inputs
    video_file = data.get('video')
    frame_number_str = data.get('frameNumber')
    video_filename = data.get('videoFileName', 'input_video.mp4')

    if not video_file or not frame_number_str:
        return web.json_response({"error": "Missing video or frameNumber"}, status=400)

    try:
        frame_number = int(frame_number_str)
    except ValueError:
        return web.json_response({"error": "frameNumber must be an integer"}, status=400)

    # Create a temporary directory to handle the files
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, video_filename)
        output_path = os.path.join(tmpdir, "frame.png")

        # Save the uploaded video to disk
        with open(input_path, 'wb') as f:
            f.write(video_file.file.read())

        # Use ffmpeg to extract the specific frame
        # -i: input file
        # -vf "select=eq(n\,FRAME_INDEX)": filter to select the specific frame index
        # -vframes 1: output only one frame
        # -q:v 2: quality (for jpeg, but we use png)
        cmd = [
            'ffmpeg',
            '-i', input_path,
            '-vf', f'select=eq(n,{frame_number})',
            '-vframes', '1',
            '-f', 'image2',
            output_path,
            '-y' # Overwrite output file if it exists
        ]

        try:
            # Run ffmpeg asynchronously
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                return web.json_response(
                    {"error": f"Frame at index {frame_number} could not be found."}, 
                    status=404
                )

            if not os.path.exists(output_path):
                return web.json_response(
                    {"error": f"Frame at index {frame_number} could not be found."}, 
                    status=404
                )

            # Read the resulting image and return it
            with open(output_path, 'rb') as f:
                image_data = f.read()

            return web.Response(body=image_data, content_type='image/png')

        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

async def init_app():
    app = web.Application()
    app.add_routes([web.post('/extract', extract_frame)])
    return app

if __name__ == '__main__':
    app = asyncio.run(init_app()) # This is a placeholder, aiohttp.web.run_app is better
    # Since we need to run the server on 0.0.0.0:5000
    web.run_app(asyncio.run(init_app()), port=5000, address='0.0.0.0')

# Correcting the run logic for aiohttp
def run_server():
    app = web.Application()
    app.add_routes([web.post('/extract', extract_frame)])
    web.run_app(app, port=5000, address='0.0.0.0')

if __name__ == '__main__':
    run_server()