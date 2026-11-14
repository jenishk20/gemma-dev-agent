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
    Creates a GIF from a set of uploaded images using ImageMagick.
    """
    # Validate targetSize format (e.g., "500x500")
    if "x" not in targetSize or not all(part.isdigit() for part in targetSize.split('x')):
        raise HTTPException(status_code=400, detail="targetSize must be in the format 'widthxheight' (e.g., 500x500)")

    # Create a temporary directory to store uploaded frames
    temp_dir = tempfile.mkdtemp()
    try:
        input_files = []
        
        # Save uploaded files to disk
        for i, image_file in enumerate(images):
            # Use a safe extension based on the filename or default to .tmp
            ext = os.path.splitext(image_file.filename)[1]
            if not ext or len(ext) > 5:
                ext = ".tmp"
            
            file_path = os.path.join(temp_dir, f"frame_{i}{ext}")
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(image_file.file, buffer)
            input_files.append(file_path)

        if not input_files:
            raise HTTPException(status_code=400, detail="No images provided")

        # Handle appendReverted logic
        # ImageMagick can handle this by duplicating the list of files in reverse order
        final_files = input_files[:]
        if appendReverted:
            # We exclude the last frame to avoid a double-frame at the peak of the animation
            # and then append the rest in reverse.
            reverted = input_files[:-1][::-1]
            final_files.extend(reverted)

        output_gif_path = os.path.join(temp_dir, "result.gif")

        # Construct ImageMagick 'convert' command
        # -delay: time between frames in ticks (usually 1/100th of a second)
        # -resize: target size
        # -loop 0: infinite loop
        
        # Note: ImageMagick delay is in 1/100s. 
        # The schema asks for milliseconds. 100ms = 10 ticks.
        im_delay = delay // 10 

        cmd = [
            "convert",
            "-delay", str(im_delay),
            "-loop", "0",
            "-resize", targetSize,
        ]
        
        # Add the input files
        cmd.extend(final_files)
        
        # Add output file
        cmd.append(output_gif_path)

        # Execute the command
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            raise HTTPException(status_code=500, detail=f"ImageMagick error: {e.stderr}")

        # Read the resulting GIF
        with open(output_gif_path, "rb") as f:
            gif_data = f.read()

        return Response(content=gif_data, media_type="image/gif")

    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Clean up temporary files
        shutil.rmtree(temp_dir)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)