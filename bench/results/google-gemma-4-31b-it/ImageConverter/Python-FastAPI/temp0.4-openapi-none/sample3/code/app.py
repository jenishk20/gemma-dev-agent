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
    Create a GIF from images using ImageMagick's convert command.
    """
    # Create a temporary directory to store uploaded frames
    temp_dir = tempfile.mkdtemp()
    try:
        input_files = []
        for i, image_file in enumerate(images):
            file_path = os.path.join(temp_dir, f"frame_{i}.png")
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(image_file.file, buffer)
            input_files.append(file_path)

        # Handle the 'appendReverted' logic: duplicate images in reverse order
        if appendReverted and len(input_files) > 1:
            # We skip the last frame to avoid double-frame at the peak of the loop
            reverted_files = input_files[-2::-1]
            for i, path in enumerate(reverted_files):
                rev_path = os.path.join(temp_dir, f"rev_{i}.png")
                shutil.copy(path, rev_path)
                input_files.append(rev_path)

        output_gif_path = os.path.join(temp_dir, "result.gif")

        # Construct ImageMagick command
        # -delay: time between frames (1/100th of a second)
        # -resize: target size (e.g., 500x500)
        # -loop 0: infinite loop
        
        # ImageMagick delay is in ticks (usually 1/100s). 
        # The schema asks for milliseconds. 100ms = 10 ticks.
        im_delay = delay // 10 

        cmd = [
            "convert",
            "-delay", str(im_delay),
            "-loop", "0",
            "-resize", targetSize,
        ] + input_files + [output_gif_path]

        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            raise HTTPException(status_code=400, detail=f"ImageMagick error: {e.stderr}")

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
        shutil.rmtree(temp_dir)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)