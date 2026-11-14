import asyncio
import os
import tempfile
import uuid
from aiohttp import web

async def extract_frame(video_path, frame_number, output_path):
    """
    Uses ffmpeg to extract a specific frame.
    -vframes 1: extract one frame
    -vf "select=eq(n,frame_number)": select the frame at the specific index
    """
    import subprocess
    
    # ffmpeg command to extract a specific frame index
    # n is the frame index (0-based)
    cmd = [
        'ffmpeg',
        '-i', video_path,
        '-vf', f'select=eq(n,{frame_number})',
        '-vframes', '1',
        '-f', 'image2',
        '-y', # overwrite output
        output_path
    ]
    
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    
    if process.returncode != 0:
        return False
    
    # ffmpeg might return 0 even if the frame index was out of bounds 
    # (it just doesn't produce a file or produces an empty one).
    # We check if the output file actually exists and has size.
    if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
        return False
        
    return True

async def handle_extract(request):
    # Handle multipart/form-data
    reader = await request.multipart()
    
    fields = {}
    video_file = None
    
    while True:
        part = await reader.next()
        if part is None:
            break
        
        if part.name == 'videoFileName':
            fields['videoFileName'] = await part.text()
        elif part.name == 'frameNumber':
            fields['frameNumber'] = await part.text()
        elif part.name == 'video':
            video_file = part
            
    if video_file is None or 'frameNumber' not in fields:
        return web.json_response({"error": "Missing video or frameNumber"}, status=400)

    try:
        frame_num = int(fields['frameNumber'])
    except ValueError:
        return web.json_response({"error": "frameNumber must be an integer"}, status=400)

    # Create temporary directory for processing
    with tempfile.TemporaryDirectory() as tmpdir:
        # Save uploaded video to temp file
        video_ext = ".mp4" # default
        if 'videoFileName' in fields:
            # Extract extension from filename
            name = fields['videoFileName']
            if '.' in name:
                video_ext = os.path.splitext(name)[1]
        
        video_path = os.path.join(tmpdir, f"input_{uuid.uuid4()}{video_ext}")
        
        with open(video_path, 'wb') as f:
            while True:
                chunk = await video_file.read_chunk()
                if not chunk:
                    break
                f.write(chunk)
        
        # Path for the extracted frame
        output_path = os.path.join(tmpdir, "frame.png")
        
        success = await extract_frame(video_path, frame_num, output_path)
        
        if not success:
            return web.json_response(
                {"error": f"Frame at index {frame_num} could not be found."}, 
                status=404
            )
        
        # Read the resulting image and return it
        with open(output_path, 'rb') as f:
            image_data = f.read()
            
        return web.Response(body=image_data, content_type='image/png')

async def init_app():
    app = web.Application()
    app.router.add_post('/extract', handle_extract)
    return app

if __name__ == '__main__':
    app = asyncio.run(init_app()) # This is a helper, but aiohttp.web.run_app is standard
    # To follow the requirement of 0.0.0.0:5000
    web.run_app(asyncio.run(init_app()), port=5000, address='0.0.0.0')

# Correction: run_app takes the app object directly.
def start():
    app = web.Application()
    app.router.add_post('/extract', handle_extract)
    web.run_app(app, port=5000, address='0.0.0.0')

if __name__ == '__main__':
    start()