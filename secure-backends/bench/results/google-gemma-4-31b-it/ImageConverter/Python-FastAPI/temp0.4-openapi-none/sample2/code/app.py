import os
import subprocess
import tempfile
import shutil
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
    # Create a temporary directory to store uploaded frames
    temp_dir = tempfile.mkdtemp()
    try:
        input_files = []
        
        # Save uploaded files to disk
        for i, image_file in enumerate(images):
            file_path = os.path.join(temp_dir, f"frame_{i}.png")
            with open(file_path, "wb") as buffer:
                content = await image_file.read()
                buffer.write(content)
            input_files.append(file_path)

        if not input_files:
            raise HTTPException(status_code=400, detail="No images provided")

        # Handle the appendReverted logic
        if appendReverted:
            # Create a reversed list of the files
            reversed_files = input_files[::-1]
            # To avoid using the same file path in the command and causing confusion 
            # with some ImageMagick versions, we can just list them twice in the command
            all_frames = input_files + reversed_files
        else:
            all_frames = input_files

        # Output path for the GIF
        output_gif_path = os.path.join(temp_dir, "result.gif")

        # Construct ImageMagick 'convert' command
        # -delay: delay between frames in ticks (1/100th of a second)
        # ImageMagick delay is in 1/100s, so 100ms = 10 ticks.
        # The schema says delay is in milliseconds.
        im_delay = str(int(delay / 10))
        
        command = [
            "convert",
            "-delay", im_delay,
            "-loop", "0",
            "-resize", targetSize,
        ] + all_frames + [output_gif_path]

        try:
            # Execute the conversion
            subprocess.run(command, check=True, capture_output=True)
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
        # Cleanup temporary directory
        shutil.rmtree(temp_dir)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)