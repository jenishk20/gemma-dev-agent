import os
import subprocess
import shutil
import tempfile
import uuid
from typing import List
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Response
from fastapi.responses import Response

app = FastAPI(title="GIF Creator API")

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
    # Validate targetSize format (e.g., 500x500)
    if not targetSize or 'x' not in targetSize:
        raise HTTPException(status_code=400, detail="targetSize must be in format WidthxHeight (e.g., 500x500)")

    # Create a unique temporary directory for this request to avoid collisions
    temp_dir = tempfile.mkdtemp(prefix=f"gif_gen_{uuid.uuid4().hex}")
    
    try:
        input_files = []
        
        # Save uploaded files to disk
        for i, image_file in enumerate(images):
            # Basic security check: avoid path traversal by ignoring filename and using index
            ext = os.path.splitext(image_file.filename)[1]
            if not ext:
                ext = ".tmp"
            
            file_path = os.path.join(temp_dir, f"frame_{i}{ext}")
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(image_file.file, buffer)
            input_files.append(file_path)

        if not input_files:
            raise HTTPException(status_code=400, detail="No images provided")

        # Handle appendReverted logic
        if appendReverted:
            # Create copies of images in reverse order
            reverted_files = []
            for i, original_path in enumerate(reversed(input_files)):
                rev_path = os.path.join(temp_dir, f"rev_{i}.tmp")
                shutil.copy(original_path, rev_path)
                reverted_files.append(rev_path)
            input_files.extend(reverted_files)

        output_gif_path = os.path.join(temp_dir, "result.gif")

        # Construct ImageMagick command
        # -delay: time between frames in ticks (1/100th of a second)
        # -resize: target size
        # -loop 0: infinite loop
        
        # Convert ms to ImageMagick ticks (1 tick = 10ms)
        delay_ticks = str(delay // 10)
        
        # Use a list for subprocess to avoid shell injection
        cmd = [
            "convert",
            "-delay", delay_ticks,
            "-loop", "0",
            "-resize", targetSize,
        ]
        
        # Add all input files
        cmd.extend(input_files)
        # Add output file
        cmd.append(output_gif_path)

        try:
            # Run the command. We use a timeout to prevent hanging processes.
            subprocess.run(cmd, check=True, timeout=30, capture_output=True)
        except subprocess.CalledProcessError as e:
            raise HTTPException(status_code=500, detail=f"ImageMagick error: {e.stderr.decode()}")
        except subprocess.TimeoutExpired:
            raise HTTPException(status_code=500, detail="Image processing timed out")

        # Read the resulting GIF
        with open(output_gif_path, "rb") as f:
            gif_content = f.read()

        return Response(content=gif_content, media_type="image/gif")

    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        # Clean up temporary files and directory
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    import uvicorn
    # Start the server on 0.0.0.0:5000
    uvicorn.run(app, host="0.0.0.0", port=5000)