import os
import subprocess
import tempfile
import shutil
from typing import List, Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Response
from fastapi.responses import Response as FastApiResponse

app = FastAPI(title="GIF Creator API")

@app.post("/create-gif")
async def create_gif(
    images: List[UploadFile] = File(...),
    targetSize: str = Form(...),
    delay: int = Form(10),
    appendReverted: bool = Form(False)
):
    """
    Create a GIF from images using ImageMagick 'convert'.
    """
    # Validate targetSize format (e.g., 500x500)
    if not targetSize or 'x' not in targetSize:
        raise HTTPException(status_code=400, detail="targetSize must be in format WxH (e.g., 500x500)")

    # Create a temporary directory to store uploaded frames
    temp_dir = tempfile.mkdtemp()
    try:
        input_files = []
        for i, image_file in enumerate(images):
            # Basic security: avoid path traversal by ignoring the filename and using a generated one
            file_path = os.path.join(temp_dir, f"frame_{i}.tmp")
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(image_file.file, buffer)
            input_files.append(file_path)

        # Handle the 'appendReverted' logic
        # ImageMagick can take a list of files; we duplicate the list in reverse order
        final_files = list(input_files)
        if appendReverted:
            final_files.extend(reversed(input_files))

        # Output path
        output_gif_path = os.path.join(temp_dir, "result.gif")

        # Build the ImageMagick command
        # -delay is in ticks (usually 1/100th of a second), so ms / 10
        # We use -resize for targetSize and -loop 0 for infinite loop
        delay_ticks = str(delay // 10)
        
        # Construct command carefully to avoid shell injection
        # We pass arguments as a list to subprocess.run
        cmd = [
            "convert",
            "-delay", delay_ticks,
            "-loop", "0",
            "-resize", targetSize,
        ]
        cmd.extend(final_files)
        cmd.append(output_gif_path)

        try:
            # Run the conversion
            subprocess.run(cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            raise HTTPException(status_code=500, detail=f"ImageMagick error: {e.stderr}")
        except FileNotFoundError:
            raise HTTPException(status_code=500, detail="ImageMagick 'convert' command not found on server.")

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
    # Start the server on 0.0.0.0:5000
    uvicorn.run(app, host="0.0.0.0", port=5000)