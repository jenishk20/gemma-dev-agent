import os
import subprocess
import tempfile
import shutil
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Response
from fastapi.responses import Response
import uvicorn

app = FastAPI(title="FrameExtract")

@app.post("/extract")
async def extract_frame(
    videoFileName: str = Form(...),
    frameNumber: int = Form(...),
    video: UploadFile = File(...)
):
    """
    Extracts a specific frame from an uploaded video using ffmpeg.
    """
    # Create a temporary directory to handle the file processing securely
    with tempfile.TemporaryDirectory() as tmpdir:
        # Sanitize filename to prevent path traversal
        safe_filename = os.path.basename(videoFileName)
        input_path = os.path.join(tmpdir, safe_filename)
        output_path = os.path.join(tmpdir, "frame.png")

        # Save the uploaded file to the temporary directory
        try:
            with open(input_path, "wb") as buffer:
                shutil.copyfileobj(video.file, buffer)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Could not save uploaded file: {e}")

        # ffmpeg command to extract a single frame
        # -i: input file
        # -vf "select=eq(n\,frame_number)": filter to select the specific frame index
        # -vframes 1: output exactly one frame
        # -q:v 2: high quality
        # We use a list for arguments to avoid shell injection (shell=False)
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
            process = subprocess.run(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                text=True, 
                check=True
            )
        except subprocess.CalledProcessError as e:
            # If ffmpeg fails, it might be because the frame index is out of bounds
            raise HTTPException(
                status_code=404, 
                detail=f"Frame at index {frameNumber} could not be found."
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Internal processing error: {e}")

        # Check if the output file was actually created
        if not os.path.exists(output_path):
            raise HTTPException(
                status_code=404, 
                detail=f"Frame at index {frameNumber} could not be found."
            )

        # Read the resulting image bytes
        with open(output_path, "rb") as image_file:
            image_bytes = image_file.read()

        return Response(content=image_bytes, media_type="image/png")

if __name__ == "__main__":
    # Start the server on 0.0.0.0:5000 as requested
    uvicorn.run(app, host="0.0.0.0", port=5000)