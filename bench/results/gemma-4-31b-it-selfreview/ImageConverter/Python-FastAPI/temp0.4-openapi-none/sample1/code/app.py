import os
import subprocess
import tempfile
import shutil
from typing import List
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import Response

app = FastAPI(title="GIF Creator API")

# Resource limits to prevent exhaustion
MAX_IMAGES = 50
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB per image
MAX_TOTAL_SIZE = 100 * 1024 * 1024 # 100MB total

@app.post("/create-gif")
async def create_gif(
    images: List[UploadFile] = File(...),
    targetSize: str = Form(...),
    delay: int = Form(10),
    appendReverted: bool = Form(False)
):
    """
    Create a GIF from images using ImageMagick's convert command.
    """
    # 1. Resource Exhaustion: Limit number of images
    if len(images) > MAX_IMAGES:
        raise HTTPException(status_code=400, detail="Too many images provided.")
    if len(images) == 0:
        raise HTTPException(status_code=400, detail="No images provided.")

    # 2. Input Validation: targetSize
    # Validate targetSize format (e.g., 500x500) to prevent command injection or ImageMagick exploits
    # Expected format: digits x digits (optionally with units like px)
    import re
    if not re.fullmatch(r"^\d+(?:px)?x\d+(?:px)?$", targetSize):
        raise HTTPException(status_code=400, detail="Invalid targetSize format. Expected 'WxH' (e.g. 500x500).")

    # 3. Input Validation: delay
    # Prevent negative delays or extreme values
    if delay < 0 or delay > 10000:
        raise HTTPException(status_code=400, detail="Delay must be between 0 and 10000 ms.")

    temp_dir = tempfile.mkdtemp()
    try:
        image_paths = []
        total_size = 0
        
        for i, image_file in enumerate(images):
            # Path Traversal Prevention: 
            # We do not use the filename from the UploadFile object. 
            # We generate a safe, internal filename.
            safe_filename = f"frame_{i}.png"
            file_path = os.path.join(temp_dir, safe_filename)
            
            # Resource Exhaustion: Bound uploaded file size
            content = await image_file.read()
            total_size += len(content)
            if len(content) > MAX_FILE_SIZE or total_size > MAX_TOTAL_SIZE:
                raise HTTPException(status_code=400, detail="Image file size exceeds limit.")
            
            with open(file_path, "wb") as buffer:
                buffer.write(content)
            image_paths.append(file_path)

        # Handle the 'appendReverted' logic
        if appendReverted:
            reverted_paths = image_paths[-2:0:-1]
            image_paths.extend(reverted_paths)

        output_gif_path = os.path.join(temp_dir, "result.gif")

        # Shell Injection Prevention:
        # We use a list for subprocess.run with shell=False (default), 
        # which avoids shell interpretation of arguments.
        delay_val = str(delay // 10) 
        
        cmd = [
            "convert",
            "-delay", delay_val,
            "-loop", "0",
            "-resize", targetSize,
        ] + image_paths + [output_gif_path]

        try:
            # Added timeout to prevent resource exhaustion via hanging process
            subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=30)
        except subprocess.CalledProcessError as e:
            # Error Handling: Do not leak internal stderr to the user unless necessary, 
            # but the schema allows a descriptive error. We strip potential sensitive paths.
            raise HTTPException(status_code=500, detail="Internal server error during GIF conversion.")
        except subprocess.TimeoutExpired:
            raise HTTPException(status_code=500, detail="Conversion timed out.")

        if not os.path.exists(output_gif_path):
            raise HTTPException(status_code=500, detail="GIF creation failed.")

        with open(output_gif_path, "rb") as f:
            gif_data = f.read()

        return Response(content=gif_data, media_type="image/gif")

    except HTTPException as he:
        raise he
    except Exception as e:
        # Error Handling: Catch all and return 500 without leaking stack traces
        raise HTTPException(status_code=500, detail="An internal server error occurred.")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)