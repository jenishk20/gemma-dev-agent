import os
import subprocess
import shutil
import tempfile
import uuid
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Response
from fastapi.responses import Response

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
    # Create a temporary directory to handle the files securely
    with tempfile.TemporaryDirectory() as tmpdir:
        # Sanitize filename to prevent path traversal attacks
        safe_video_name = f"{uuid.uuid4()}_{os.path.basename(videoFileName)}"
        input_path = os.path.join(tmpdir, safe_video_name)
        output_path = os.path.join(tmpdir, "frame.png")

        try:
            # Save the uploaded video to the temporary directory
            with open(input_path, "wb") as buffer:
                shutil.copyfileobj(video.file, buffer)

            # ffmpeg command: 
            # -i: input file
            # -vf "select=not(mod(n,1))": filter to select frames
            # -vframes 1: output exactly one frame
            # The 'select' filter with 'eq(n, X)' is the most precise way to get frame X
            # n is the frame index (0-based)
            cmd = [
                "ffmpeg",
                "-i", input_path,
                "-vf", f"select=eq(n,{frameNumber})",
                "-vframes", "1",
                "-f", "image2",
                "-y", # Overwrite output file if exists
                output_path
            ]

            # Run ffmpeg. stderr is captured to check for errors.
            process = subprocess.run(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                text=True
            )

            # If ffmpeg failed or the output file wasn't created, the frame index might be out of range
            if process.returncode != 0 or not os.path.exists(output_path):
                raise HTTPException(
                    status_code=404, 
                    detail=f"Frame at index {frameNumber} could not be found."
                )

            # Read the resulting image file
            with open(output_path, "rb") as image_file:
                image_bytes = image_file.read()

            return Response(content=image_bytes, media_type="image/png")

        except HTTPException as he:
            raise he
        except Exception as e:
            # Generic error handling for unexpected failures
            raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    # Start the server on 0.0.0.0:5000 as requested
    uvicorn.run(app, host="0.0.0.0", port=5000)