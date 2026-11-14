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
    # Create a temporary directory to store uploaded frames
    temp_dir = tempfile.mkdtemp()
    try:
        input_files = []
        
        # Save uploaded files to disk
        for i, image_file in enumerate(images):
            file_path = os.path.join(temp_dir, f"frame_{i}.png")
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(image_file.file, buffer)
            input_files.append(file_path)

        if not input_files:
            raise HTTPException(status_code=400, detail="No images provided")

        # Handle the appendReverted logic
        # ImageMagick can handle this by duplicating the list in reverse
        if appendReverted:
            # We create copies of the files in reverse order to ensure they are distinct paths
            # or simply pass the paths again in reverse order to the command line.
            frames = input_files + input_files[::-1]
        else:
            frames = input_files

        # Define output path
        output_gif = os.path.join(temp_dir, "result.gif")

        # Build the ImageMagick convert command
        # -delay: time between frames in ticks (1/100th of a second). 
        # The schema asks for milliseconds, so delay / 10.
        # -resize: targetSize (e.g., 500x500)
        # -loop 0: infinite loop
        
        delay_ticks = str(int(delay / 10))
        
        cmd = [
            "convert",
            "-delay", delay_ticks,
            "-loop", "0",
            "-resize", targetSize,
        ] + frames + [output_gif]

        try:
            # Run the conversion
            subprocess.run(cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            raise HTTPException(status_code=500, detail=f"ImageMagick error: {e.stderr}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

        # Read the resulting GIF
        with open(output_gif, "rb") as f:
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