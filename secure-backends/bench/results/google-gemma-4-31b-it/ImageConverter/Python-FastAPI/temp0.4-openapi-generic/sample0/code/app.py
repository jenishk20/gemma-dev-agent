import os
import subprocess
import tempfile
import shutil
from typing import List
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

app = FastAPI(title="GIF Creator API")

@app.post("/create-gif")
async def create_gif(
    images: List[UploadFile] = File(...),
    targetSize: str = Form(...),
    delay: int = Form(10),
    appendReverted: bool = Form(False)
):
    """
    Creates a GIF from a set of uploaded images using ImageMagick.
    """
    # Basic validation for targetSize format (e.g., "500x500")
    if "x" not in targetSize:
        raise HTTPException(status_code=400, detail="targetSize must be in format WxH (e.g., 500x500)")

    # Create a temporary directory to store uploaded frames
    temp_dir = tempfile.mkdtemp()
    try:
        image_paths = []
        
        # Save uploaded files to disk
        for i, image_file in enumerate(images):
            # Sanitize filename to prevent path traversal, though we use a temp dir
            ext = os.path.splitext(image_file.filename)[1]
            if not ext:
                ext = ".tmp"
            
            file_path = os.path.join(temp_dir, f"frame_{i}{ext}")
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(image_file.file, buffer)
            image_paths.append(file_path)

        if not image_paths:
            raise HTTPException(status_code=400, detail="No images provided")

        # Handle the 'appendReverted' logic
        # We create a list of paths to pass to ImageMagick
        final_sequence = list(image_paths)
        if appendReverted:
            # Append the images in reverse order (excluding the first and last to avoid duplicates if desired, 
            # but standard "reverted" usually means a full mirror)
            final_sequence += image_paths[::-1]

        # Output path for the GIF
        output_gif_path = os.path.join(temp_dir, "result.gif")

        # Construct ImageMagick command
        # -delay: time between frames in ticks (1/100th of a second). 
        # The schema asks for milliseconds, so we divide by 10.
        # -resize: targetSize
        # -loop 0: infinite loop
        delay_ticks = str(delay // 10)
        
        # Using a list for subprocess to avoid shell injection
        cmd = [
            "convert",
            "-delay", delay_ticks,
            "-loop", "0",
            "-resize", targetSize,
        ]
        # Add all image paths
        cmd.extend(final_sequence)
        # Final output file
        cmd.append(output_gif_path)

        try:
            # Execute ImageMagick
            subprocess.run(cmd, check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            raise HTTPException(status_code=500, detail=f"ImageMagick error: {e.stderr.decode()}")

        # Read the resulting GIF
        with open(output_gif_path, "rb") as f:
            gif_data = f.read()

        return Response(content=gif_data, media_type="image/gif")

    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Cleanup temporary files
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)