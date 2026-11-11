import os
import subprocess
import tempfile
import shutil
from typing import Annotated

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Response
from pydantic import BaseModel

app = FastAPI(title="FrameExtract")

@app.post("/extract")
async def extract_frame(
    videoFileName: Annotated[str, Form()],
    frameNumber: Annotated[int, Form()],
    video: Annotated[UploadFile, File()]
):
    """
    Extracts a specific frame from an uploaded video using ffmpeg.
    """
    # Create a temporary directory to handle files securely
    with tempfile.TemporaryDirectory() as tmpdir:
        # Sanitize filename to prevent path traversal
        safe_filename = os.path.basename(videoFileName)
        input_path = os.path.join(tmpdir, safe_filename)
        output_path = os.path.join(tmpdir, "frame.png")

        # Save the uploaded video to the temporary path
        try:
            with open(input_path, "wb") as buffer:
                shutil.copyfileobj(video.file, buffer)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Could not save uploaded file: {e}")

        # ffmpeg command to extract a specific frame
        # -i: input file
        # -vf "select=eq(n\,frameNumber)": filter to select the specific frame index
        # -vframes 1: output exactly one frame
        # -q:v 2: high quality
        cmd = [
            "ffmpeg",
            "-i", input_path,
            "-vf", f"select=eq(n\\,{frameNumber})",
            "-vframes", "1",
            "-f", "image2",
            "-y", # Overwrite output file if it exists
            output_path
        ]

        try:
            # Run ffmpeg. stderr is captured to check for errors.
            result = subprocess.run(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                check=True,
                text=True
            )
        except subprocess.CalledProcessError:
            # If ffmpeg fails, it might be because the frame index is out of range
            raise HTTPException(
                status_code=404, 
                detail=f"Frame at index {frameNumber} could not be found."
            )
        except FileNotFoundError:
            raise HTTPException(status_code=500, detail="ffmpeg not installed on server.")

        # Verify if the output file was actually created
        if not os.path.exists(output_path):
            raise HTTPException(
                status_code=404, 
                detail=f"Frame at index {frameNumber} could not be found."
            )

        # Read the extracted image into memory
        with open(output_path, "rb") as image_file:
            image_bytes = image_file.read()

        return Response(content=image_bytes, media_type="image/png")

if __name__ == "__main__":
    import uvicorn
    # Start the server on 0.0.0.0:5000 as requested
    uvicorn.run(app, host="0.0.0.0", port=5000)