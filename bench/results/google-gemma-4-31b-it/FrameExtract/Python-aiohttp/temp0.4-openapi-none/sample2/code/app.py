import asyncio
import os
import tempfile
import uuid
from aiohttp import web

async def extract_frame(request):
    """
    Handler to extract a specific frame from an uploaded video using ffmpeg.
    """
    try:
        # Parse multipart form data
        data = await request.post()
        
        # Extract fields
        video_file = data.get('video')
        frame_number_str = data.get('frameNumber')
        
        if not video_file or not frame_number_str:
            return web.json_response({"error": "Missing required fields: video and frameNumber"}, status=400)
        
        try:
            frame_number = int(frame_number_str)
        except ValueError:
            return web.json_response({"error": "frameNumber must be an integer"}, status=400)

        # Create a temporary directory to handle files
        with tempfile.TemporaryDirectory() as tmpdir:
            # Save uploaded video to disk
            video_filename = f"{uuid.uuid4()}.mp4"
            video_path = os.path.join(tmpdir, video_filename)
            
            # Read the binary content of the uploaded file
            content = await video_file.read()
            with open(video_path, 'wb') as f:
                f.write(content)
            
            # Output path for the extracted frame
            output_path = os.path.join(tmpdir, "frame.png")
            
            # FFmpeg command: 
            # -i: input file
            # -vf "select=not(mod(n\,1) && n!=X)": select frame X (0-indexed)
            # -vframes 1: output exactly one frame
            # -f image2: force image format
            cmd = [
                'ffmpeg',
                '-i', video_path,
                '-vf', f'select=eq(n,{frame_number})',
                '-vframes', '1',
                '-f', 'image2',
                output_path,
                '-y' # Overwrite output files
            ]
            
            # Run ffmpeg as a subprocess
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

    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

async def init_app():
    app = web.Application()
    app.add_routes([web.post('/extract', extract_frame)])
    return app

if __name__ == '__main__':
    app = asyncio.run(init_app()) # This is a placeholder, we use web.run_app
    # Since we need to start the server on 0.0.0.0:5000
    # We redefine the logic to use web.run_app directly
    
# Re-structuring for a clean run_app call
def run_server():
    app = web.Application()
    app.add_routes([web.post('/extract', extract_frame)])
    web.run_app(app, host='0.0.0.0', port=5000)

if __name__ == '__main__':
    run_server()