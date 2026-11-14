import os
import subprocess
import tempfile
import shutil
import re
from typing import List
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import Response

app = FastAPI(title="GIF Creator API")

# Security Constants
MAX_FILES = 50  # Prevent resource exhaustion (too many files)
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB per image to prevent resource exhaustion
MAX_TOTAL_SIZE = 100 * 1024 * 1024  # 100MB total request size

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
    # 1. Input Validation: targetSize
    # Validate targetSize to prevent command injection or ImageMagick exploits.
    # Expected format: "widthxheight" (e.g., 500x500)
    if not re.match(r"^\d+x\d+$", targetSize):
        raise HTTPException(status_code=400, detail="Invalid targetSize format. Expected widthxheight (e.g. 500x500)")

    # 2. Resource Exhaustion: Limit number of files
    if len(images) > MAX_FILES:
        raise HTTPException(status_code=400, detail=f"Too many images. Maximum allowed is {MAX_FILES}")
    
    if len(images) == 0:
        raise HTTPException(status_code=400, detail="No images provided")

    # Create a temporary directory to store uploaded frames
    temp_dir = tempfile.mkdtemp()
    try:
        input_files = []
        total_bytes_received = 0
        
        # Save uploaded files to disk
        for i, image_file in enumerate(images):
            # Security: We generate the filename ourselves, ignoring the client-provided filename
            # to prevent path traversal attacks.
            file_path = os.path.join(temp_dir, f"frame_{i}.png")
            
            # Resource Exhaustion: Bound the size of each uploaded file
            content = await image_file.read()
            file_size = len(content)
            total_bytes_received += file_size
            
            if file_size > MAX_FILE_SIZE:
                raise HTTPException(status_code=400, detail="Individual image file size exceeds limit")
            if total_bytes_received > MAX_TOTAL_SIZE:
                raise HTTPException(status_code=400, detail="Total upload size exceeds limit")

            with open(file_path, "wb") as buffer:
                buffer.write(content)
            input_files.append(file_path)

        # Handle the appendReverted logic
        if appendReverted:
            frames = input_files + input_files[::-1]
        else:
            frames = input_files

        # Define output path
        output_gif = os.path.join(temp_dir, "result.gif")

        # 3. Command Injection Prevention:
        # We use a list for subprocess.run with shell=False (default), which avoids the shell.
        # We have already validated targetSize via regex.
        # delay is cast to int, preventing injection.
        
        # ImageMagick delay is in 1/100s of a second.
        # Ensure delay is non-negative.
        if delay < 0:
            raise HTTPException(status_code=400, detail="Delay cannot be negative")
        
        delay_ticks = str(int(delay // 10))
        
        cmd = [
            "convert",
            "-delay", delay_ticks,
            "-loop", "0",
            "-resize", targetSize,
        ] + frames + [output_gif]

        try:
            # Use a timeout to prevent DoS via "image bombs" (resource exhaustion)
            subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=60)
        except subprocess.TimeoutExpired:
            raise HTTPException(status_code=500, detail="Image processing timed out")
        except subprocess.CalledProcessError as e:
            # Error Handling: Do not leak internal stderr to the user if it contains sensitive paths,
            # but the schema requires a detail message. We provide a generic error.
            raise HTTPException(status_code=500, detail="Internal server error during image conversion")
        except Exception:
            raise HTTPException(status_code=500, detail="Internal server error")

        # Read the resulting GIF
        if not os.path.exists(output_gif):
            raise HTTPException(status_code=500, detail="GIF was not created successfully")
            
        with open(output_gif, "rb") as f:
            gif_data = f.read()

        return Response(content=gif_data, media_type="image/gif")

    except HTTPException as he:
        raise he
    except Exception as e:
        # Generic error handling to avoid leaking stack traces
        raise HTTPException(status_code=500, detail="An unexpected error occurred")
    finally:
        # Clean up temporary directory
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)