import os
import subprocess
import tempfile
import shutil
import re
from typing import List
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Response
import uvicorn

app = FastAPI(title="GIF Creator API")

# Resource exhaustion limits
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
    Create a GIF from images using ImageMagick 'convert' command.
    """
    # 1. Resource Exhaustion: Limit number of images
    if len(images) > MAX_IMAGES:
        raise HTTPException(status_code=400, detail="Too many images provided.")
    if len(images) == 0:
        raise HTTPException(status_code=400, detail="No images provided.")

    # 2. Input Validation: targetSize must be in format WxH (e.g., 500x500)
    # This prevents command injection or passing malicious flags to ImageMagick
    if not re.match(r"^\d+x\d+$", targetSize):
        raise HTTPException(status_code=400, detail="Invalid targetSize format. Expected WxH (e.g. 500x500).")

    # 3. Input Validation: delay
    if delay < 0 or delay > 10000:
        raise HTTPException(status_code=400, detail="Delay must be between 0 and 10000 ms.")

    temp_dir = tempfile.mkdtemp()
    try:
        input_files = []
        total_size = 0
        
        for i, image_file in enumerate(images):
            # Resource Exhaustion: Check individual file size
            # We read in chunks to avoid loading huge files into memory
            file_path = os.path.join(temp_dir, f"frame_{i}.png")
            
            current_file_size = 0
            with open(file_path, "wb") as buffer:
                while True:
                    chunk = await image_file.read(8192)
                    if not chunk:
                        break
                    current_file_size += len(chunk)
                    buffer.write(chunk)
            
            if current_file_size > MAX_FILE_SIZE:
                raise HTTPException(status_code=400, detail=f"Image {i} exceeds size limit.")
            
            total_size += current_file_size
            if total_size > MAX_TOTAL_SIZE:
                raise HTTPException(status_code=400, detail="Total upload size exceeds limit.")
            
            input_files.append(file_path)

        if appendReverted:
            reverted_files = []
            for i, path in enumerate(reversed(input_files)):
                rev_path = os.path.join(temp_dir, f"rev_{i}.png")
                shutil.copy2(path, rev_path)
                reverted_files.append(rev_path)
            input_files.extend(reverted_files)

        output_gif_path = os.path.join(temp_dir, "result.gif")

        # ImageMagick 'convert' command
        # Use a list for subprocess.run to avoid shell=True (prevents shell injection)
        im_delay = delay // 10

        cmd = [
            "convert",
            "-delay", str(im_delay),
            "-loop", "0",
            "-resize", targetSize,
        ]
        cmd.extend(input_files)
        cmd.append(output_gif_path)

        try:
            # Use timeout to prevent resource exhaustion (DoS) via long-running processes
            subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=60)
        except subprocess.TimeoutExpired:
            raise HTTPException(status_code=500, detail="GIF processing timed out.")
        except subprocess.CalledProcessError as e:
            # Avoid leaking internal ImageMagick stack traces in production, 
            # but the schema allows a descriptive error for 400.
            raise HTTPException(status_code=400, detail="ImageMagick failed to process images.")

        with open(output_gif_path, "rb") as f:
            gif_content = f.read()

        return Response(content=gif_content, media_type="image/gif")

    except HTTPException as e:
        raise e
    except Exception:
        # General catch-all to prevent leaking internal server details/stack traces
        raise HTTPException(status_code=500, detail="An internal server error occurred.")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)