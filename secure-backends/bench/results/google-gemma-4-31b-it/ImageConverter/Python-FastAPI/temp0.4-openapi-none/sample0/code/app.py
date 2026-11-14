import os
import subprocess
import tempfile
import shutil
from typing import List
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Response
from fastapi.responses import Response
import uvicorn

app = FastAPI(title="GIF Creator API")

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
    # Create a temporary directory to store uploaded frames
    temp_dir = tempfile.mkdtemp()
    try:
        input_files = []
        for i, image_file in enumerate(images):
            # Save each uploaded file to the temp directory
            file_path = os.path.join(temp_dir, f"frame_{i}.png")
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(image_file.file, buffer)
            input_files.append(file_path)

        # If appendReverted is true, duplicate the list in reverse order
        if appendReverted:
            # We create copies of the files to avoid ImageMagick issues with 
            # referencing the same file multiple times in some versions
            reverted_files = []
            for i, path in enumerate(reversed(input_files)):
                rev_path = os.path.join(temp_dir, f"rev_{i}.png")
                shutil.copy2(path, rev_path)
                reverted_files.append(rev_path)
            input_files.extend(reverted_files)

        output_gif_path = os.path.join(temp_dir, "result.gif")

        # ImageMagick 'convert' command construction
        # -delay: time between frames (1/100ths of a second)
        # -resize: target size (e.g., 500x500)
        # -loop 0: infinite loop
        
        # Note: The OpenAPI says delay is in milliseconds. 
        # ImageMagick -delay is in ticks (usually 1/100s).
        # 100ms = 10 ticks.
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
            subprocess.run(cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            raise HTTPException(status_code=400, detail=f"ImageMagick error: {e.stderr}")

        # Read the resulting GIF
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
    uvicorn.run(app, host="0.0.0.0", port=5000)