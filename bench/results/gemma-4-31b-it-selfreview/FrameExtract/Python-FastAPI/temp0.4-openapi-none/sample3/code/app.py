import os
import subprocess
import tempfile
import uvicorn
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Response
from typing import Annotated

app = FastAPI(title="FrameExtract")

# Define a reasonable limit for uploaded files to prevent resource exhaustion (e.g., 100MB)
MAX_FILE_SIZE = 100 * 1024 * 1024 

@app.post("/extract")
async def extract_frame(
    videoFileName: Annotated[str, Form()],
    frameNumber: Annotated[int, Form()],
    video: UploadFile = File(...)
):
    """
    Extracts a specific frame from an uploaded video using ffmpeg.
    """
    # 1. Resource Exhaustion: Validate frameNumber is non-negative
    if frameNumber < 0:
        raise HTTPException(
            status_code=404, 
            detail=f"Frame at index {frameNumber} could not be found."
        )

    # Create a temporary directory to handle the files
    with tempfile.TemporaryDirectory() as tmpdir:
        # 2. Path Traversal: Sanitize videoFileName
        # We ignore the user-provided path and only take the basename to prevent traversal
        safe_filename = os.path.basename(videoFileName)
        if not safe_filename:
            safe_filename = "input_video.tmp"
            
        input_path = os.path.join(tmpdir, safe_filename)
        output_path = os.path.join(tmpdir, "frame.png")

        # 3. Resource Exhaustion: Bound request size
        try:
            content = await video.read()
            if len(content) > MAX_FILE_SIZE:
                raise HTTPException(status_code=413, detail="File too large")
            
            with open(input_path, "wb") as buffer:
                buffer.write(content)
        except HTTPException:
            raise
        except Exception as e:
            # 4. Error Handling: Avoid leaking internal details
            raise HTTPException(status_code=500, detail="Internal server error occurred during upload")

        # 5. Shell Injection: Use a list of arguments with subprocess.run (shell=False by default)
        # This prevents untrusted input from reaching a shell.
        cmd = [
            "ffmpeg",
            "-i", input_path,
            "-vf", f"select=eq(n,{frameNumber})",
            "-vframes", "1",
            "-f", "image2",
            output_path
        ]

        try:
            # Run ffmpeg with a timeout to prevent resource exhaustion (DoS via long-running process)
            process = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=30,
                shell=False 
            )
            
            if process.returncode != 0 or not os.path.exists(output_path):
                raise HTTPException(
                    status_code=404, 
                    detail=f"Frame at index {frameNumber} could not be found."
                )

            with open(output_path, "rb") as img_file:
                image_bytes = img_file.read()

            return Response(content=image_bytes, media_type="image/png")

        except subprocess.TimeoutExpired:
            raise HTTPException(status_code=500, detail="Processing timed out")
        except subprocess.CalledProcessError:
            raise HTTPException(
                status_code=404, 
                detail=f"Frame at index {frameNumber} could not be found."
            )
        except Exception as e:
            if isinstance(e, HTTPException):
                raise e
            # 4. Error Handling: Generic error to avoid leaking stack traces
            raise HTTPException(status_code=500, detail="An error occurred during frame extraction")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)