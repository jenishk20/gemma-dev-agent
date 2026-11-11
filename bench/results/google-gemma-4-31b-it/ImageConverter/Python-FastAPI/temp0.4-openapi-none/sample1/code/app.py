import os
import subprocess
import tempfile
import shutil
from typing import List
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
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
    Create a GIF from images using ImageMagick's convert command.
    """
    # Create a temporary directory to hold the uploaded images
    temp_dir = tempfile.mkdtemp()
    try:
        image_paths = []
        
        # Save uploaded files to the temp directory
        for i, image_file in enumerate(images):
            file_path = os.path.join(temp_dir, f"frame_{i}.png")
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(image_file.file, buffer)
            image_paths.append(file_path)

        if not image_paths:
            raise HTTPException(status_code=400, detail="No images provided")

        # Handle the 'appendReverted' logic (ping-pong effect)
        if appendReverted:
            # Append images in reverse order, excluding the first and last to avoid duplicates
            # if the list is [1, 2, 3], reversed is [3, 2, 1]. 
            # To avoid double frames at the ends, we take [2]
            reverted_paths = image_paths[-2:0:-1]
            image_paths.extend(reverted_paths)

        # Output path for the resulting GIF
        output_gif_path = os.path.join(temp_dir, "result.gif")

        # ImageMagick 'convert' command construction
        # -delay is in hundredths of a second (100ms = 10)
        # -resize is for targetSize (e.g., 500x500)
        # -loop 0 makes it an infinite loop
        delay_val = str(delay // 10) 
        
        cmd = [
            "convert",
            "-delay", delay_val,
            "-loop", "0",
            "-resize", targetSize,
        ] + image_paths + [output_gif_path]

        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            raise HTTPException(status_code=500, detail=f"ImageMagick error: {e.stderr}")

        # Read the resulting GIF file
        with open(output_gif_path, "rb") as f:
            gif_data = f.read()

        return Response(content=gif_data, media_type="image/gif")

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Clean up temporary directory
        shutil.rmtree(temp_dir)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)