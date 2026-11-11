import os
import subprocess
import tempfile
import shutil
from typing import List
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Response

app = FastAPI(title="GIF Creator API")

# Resource exhaustion limits
MAX_FILES = 50
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB per image
MAX_TOTAL_SIZE = 100 * 1024 * 1024  # 100MB total

@app.post("/create-gif")
async def create_gif(
    images: List[UploadFile] = File(...),
    targetSize: str = Form(...),
    delay: int = Form(10),
    appendReverted: bool = Form(False)
):
    """
    Create a GIF from images using ImageMagick.
    """
    # 1. Resource Exhaustion: Limit number of files
    if len(images) > MAX_FILES:
        raise HTTPException(status_code=400, detail="Too many images provided")
    if len(images) == 0:
        raise HTTPException(status_code=400, detail="No images provided")

    # 2. Input Validation: targetSize must be in format 'WxH' to prevent command injection/errors
    # ImageMagick resize expects something like '500x500' or '500x'
    # We validate that it only contains digits, 'x', and potentially '%' or '!' (standard IM geometry)
    import re
    if not re.match(r"^\d+x\d+([@!%]?)$", targetSize) and not re.match(r"^\d+x([@!%]?)$", targetSize):
        raise HTTPException(status_code=400, detail="Invalid targetSize format. Expected WxH (e.g., 500x500)")

    # 3. Input Validation: delay should be non-negative
    if delay < 0:
        raise HTTPException(status_code=400, detail="Delay cannot be negative")

    # Create a temporary directory to store uploaded frames
    temp_dir = tempfile.mkdtemp()
    try:
        input_files = []
        total_size = 0
        
        # Save uploaded files to disk
        for i, image_file in enumerate(images):
            # Path Traversal Prevention: 
            # We ignore the filename provided by the user (image_file.filename) 
            # and generate our own safe filename.
            file_path = os.path.join(temp_dir, f"frame_{i}.png")
            
            # Resource Exhaustion: Bound request sizes
            content = await image_file.read()
            file_size = len(content)
            total_size += file_size
            
            if file_size > MAX_FILE_SIZE or total_size > MAX_TOTAL_SIZE:
                raise HTTPException(status_code=400, detail="Uploaded files exceed size limits")
                
            with open(file_path, "wb") as buffer:
                buffer.write(content)
            input_files.append(file_path)

        # Handle the appendReverted logic
        if appendReverted:
            all_frames = input_files + input_files[::-1]
        else:
            all_frames = input_files

        # Output path for the GIF
        output_gif_path = os.path.join(temp_dir, "result.gif")

        # ImageMagick delay is in 1/100s, so 100ms = 10 ticks.
        im_delay = str(int(delay / 10))
        
        # Shell Injection Prevention:
        # We use a list for subprocess.run (shell=False by default), 
        # which avoids shell interpolation.
        command = [
            "convert",
            "-delay", im_delay,
            "-loop", "0",
            "-resize", targetSize,
        ] + all_frames + [output_gif_path]

        try:
            # Execute the conversion with a timeout to prevent DoS via "image bombs"
            subprocess.run(command, check=True, capture_output=True, timeout=60)
        except subprocess.TimeoutExpired:
            raise HTTPException(status_code=500, detail="Image processing timed out")
        except subprocess.CalledProcessError as e:
            # Error Handling: Do not leak internal stack traces, return documented error
            raise HTTPException(status_code=500, detail="Internal server error during GIF creation")

        # Read the resulting GIF
        if not os.path.exists(output_gif_path):
            raise HTTPException(status_code=500, detail="GIF was not created successfully")

        with open(output_gif_path, "rb") as f:
            gif_data = f.read()

        return Response(content=gif_data, media_type="image/gif")

    except HTTPException as e:
        raise e
    except Exception:
        # Error Handling: Catch all and return 500 without leaking internals
        raise HTTPException(status_code=500, detail="An unexpected error occurred on the server")
    finally:
        # Cleanup temporary directory
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)