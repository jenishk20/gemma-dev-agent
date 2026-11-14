import os
import subprocess
import tempfile
import shutil
from typing import List
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Response

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
    Create a GIF from images using ImageMagick's convert command.
    """
    # 1. Resource Exhaustion: Limit number of images
    if len(images) > MAX_IMAGES:
        raise HTTPException(status_code=400, detail="Too many images provided.")
    if len(images) == 0:
        raise HTTPException(status_code=400, detail="No images provided.")

    # 2. Input Validation: targetSize
    # Expected format: widthxheight (e.g., 500x500). 
    # We validate this to prevent command injection via ImageMagick flags.
    import re
    if not re.match(r"^\d+x\d+$", targetSize):
        raise HTTPException(status_code=400, detail="Invalid targetSize format. Expected 'widthxheight' (e.g. 500x500).")

    # 3. Input Validation: delay
    if delay < 0 or delay > 10000: # Reasonable upper bound (10s)
        raise HTTPException(status_code=400, detail="Delay must be between 0 and 10000 milliseconds.")

    # Create a temporary directory to store uploaded frames
    temp_dir = tempfile.mkdtemp()
    try:
        input_files = []
        total_bytes_received = 0
        
        for i, image_file in enumerate(images):
            # Resource Exhaustion: Check individual file size
            # Note: image_file.size might be None depending on the client
            content = await image_file.read()
            file_size = len(content)
            total_bytes_received += file_size
            
            if file_size > MAX_FILE_SIZE:
                raise HTTPException(status_code=400, detail=f"Image {i} exceeds maximum size limit.")
            if total_bytes_received > MAX_TOTAL_SIZE:
                raise HTTPException(status_code=400, detail="Total upload size exceeds limit.")

            # Path Traversal Prevention: 
            # We ignore the filename provided by the user and generate our own safe name.
            file_path = os.path.join(temp_dir, f"frame_{i}.png")
            with open(file_path, "wb") as buffer:
                buffer.write(content)
            input_files.append(file_path)

        # Handle the 'appendReverted' logic
        if appendReverted and len(input_files) > 1:
            reverted_files = input_files[-2::-1]
            for i, path in enumerate(reverted_files):
                rev_path = os.path.join(temp_dir, f"rev_{i}.png")
                shutil.copy(path, rev_path)
                input_files.append(rev_path)

        output_gif_path = os.path.join(temp_dir, "result.gif")

        # Command Injection Prevention:
        # We use a list for subprocess.run (shell=False by default), which avoids shell interpolation.
        # We have already validated targetSize and delay.
        im_delay = delay // 10 

        cmd = [
            "convert",
            "-delay", str(im_delay),
            "-loop", "0",
            "-resize", targetSize,
        ] + input_files + [output_gif_path]

        try:
            # Use a timeout to prevent resource exhaustion (hanging processes)
            subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=60)
        except subprocess.TimeoutExpired:
            raise HTTPException(status_code=500, detail="Image processing timed out.")
        except subprocess.CalledProcessError as e:
            # Error Handling: Do not leak internal stack traces, return 400 for bad inputs
            raise HTTPException(status_code=400, detail="ImageMagick failed to process images.")

        # Read the resulting GIF
        if not os.path.exists(output_gif_path):
            raise HTTPException(status_code=500, detail="GIF was not created.")
            
        with open(output_gif_path, "rb") as f:
            gif_data = f.read()

        return Response(content=gif_data, media_type="image/gif")

    except HTTPException as he:
        raise he
    except Exception:
        # Error Handling: Generic 500 error to avoid leaking internal details
        raise HTTPException(status_code=500, detail="An internal server error occurred.")
    finally:
        # Cleanup temporary files
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)