import subprocess
import os
import tempfile
import uvicorn
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Response
from typing import Optional

app = FastAPI(title="FrameExtract")

@app.post("/extract")
async def extract_frame(
    videoFileName: str = Form(...),
    frameNumber: int = Form(...),
    video: UploadFile = File(...)
):
    # Create a temporary directory to handle the files
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, video.filename)
        output_path = os.path.join(tmpdir, "frame.png")

        # Save the uploaded video to disk
        try:
            content = await video.read()
            with open(input_path, "wb") as f:
                f.write(content)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Could not save uploaded video: {str(e)}")

        # Use ffmpeg to extract the specific frame
        # -i: input file
        # -vf "select=eq(n,X)": filter to select frame index X
        # -vframes 1: output exactly one frame
        # -f image2: force image format
        cmd = [
            "ffmpeg",
            "-i", input_path,
            "-vf", f"select=eq(n,{frameNumber})",
            "-vframes", "1",
            "-f", "image2",
            output_path
        ]

        try:
            # Run ffmpeg and capture output to check for errors
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        except subprocess.CalledProcessError:
            # If ffmpeg fails, it's likely the frame index is out of bounds
            raise HTTPException(
                status_code=404, 
                detail=f"Frame at index {frameNumber} could not be found."
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

        # Check if the output file was actually created
        if not os.path.exists(output_path):
            raise HTTPException(
                status_code=404, 
                detail=f"Frame at index {frameNumber} could not be found."
            )

        # Read the image and return it as a response
        with open(output_path, "rb") as f:
            image_bytes = f.read()

        return Response(content=image_bytes, media_type="image/png")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)