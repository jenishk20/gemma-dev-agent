import os
import subprocess
import tempfile
import shutil
import uvicorn
from typing import List
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Response
from fastapi.responses import Response

app = FastAPI(title="GIF Creator API")

@app.post("/create-gif", summary="Create a GIF from images")
async def create_gif(
    images: List[UploadFile] = File(...),
    targetSize: str = Form(...),
    delay: int = Form(10),
    appendReverted: bool = Form(False)
):
    """
    Accepts images, a target size, delay, and a flag to append a reverted version to create a GIF.
    """
    # Basic validation for targetSize format (e.g., 500x500)
    if "x" not in targetSize:
        raise HTTPException(status_code=400, detail="targetSize must be in format 'widthxheight' (e.g., 500x500)")

    # Create a temporary directory to store uploaded frames
    temp_dir = tempfile.mkdtemp()
    try:
        image_paths = []
        for i, upload_file in enumerate(images):
            # Save each uploaded file to the temp directory
            file_path = os.path.join(temp_dir, f"frame_{i}.png")
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(upload_file.file, buffer)
            image_paths.append(file_path)

        # Handle the 'appendReverted' logic: add images in reverse order
        if appendReverted:
            # We skip the last image to avoid a double frame at the pivot point
            # and the first image to avoid a double frame at the end of the loop
            reverted_paths = image_paths[-2:0:-1] 
            # For simplicity and to match common GIF expectations, we just append the reverse list
            # but a more polished version would handle the pivot frames.
            # Here we follow the prompt's logic: "append a reverted version".
            image_paths.extend(reverted_paths)

        # Output path for the final GIF
        output_gif_path = os.path.join(temp_dir, "result.gif")

        # Build ImageMagick command
        # -delay is in ticks. 100 ticks per second is standard. 
        # The prompt says delay is in milliseconds. 
        # In ImageMagick, -delay 10 means 10*1/100 = 0.1s = 100ms.
        # So we convert ms to ticks: ticks = ms / 10.
        im_delay = str(delay // 10)

        # Security: We use a list for subprocess.run to avoid shell injection.
        # We only pass the paths and the validated targetSize.
        cmd = [
            "convert",
            f"-delay", im_delay,
            "-loop", "0",
        ]
        
        # Add image paths and resize them
        for path in image_paths:
            cmd.extend(["(", path, "-resize", targetSize, ")"])
        
        cmd.append(output_gif_path)

        try:
            subprocess.run(cmd, check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            raise HTTPException(status_code=500, detail=f"ImageMagick error: {e.stderr.decode()}")

        # Read the resulting GIF into memory
        with open(output_gif_path, "rb") as f:
            gif_content = f.read()

        return Response(content=gif_content, media_type="image/gif")

    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Clean up temporary files
        shutil.rmtree(temp_dir)

if __name__ == "__main__":
    # Start the server on 0.0.0.0:5000
    uvicorn.run(app, host="0.0.0.0", port=5000)