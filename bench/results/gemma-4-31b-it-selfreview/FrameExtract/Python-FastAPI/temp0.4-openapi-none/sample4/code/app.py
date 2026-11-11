import os
import subprocess
import tempfile
import uvicorn
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Response
from typing import Annotated

app = FastAPI(title="FrameExtract")

# Limit the maximum upload size to prevent resource exhaustion (e.g., 100MB)
MAX_UPLOAD_SIZE = 100 * 1024 * 1024 

@app.post("/extract")
async def extract_frame(
    videoFileName: Annotated[str, Form()],
    frameNumber: Annotated[int, Form()],
    video: Annotated[UploadFile, File()]
):
    # 1. Resource Exhaustion: Validate frameNumber is non-negative
    if frameNumber < 0:
        raise HTTPException(status_code=404, detail=f"Frame at index {frameNumber} could not be found.")

    # 2. Path Traversal: Sanitize videoFileName
    # We extract only the base name to prevent absolute paths or '..' traversal
    safe_filename = os.path.basename(videoFileName)
    if not safe_filename or safe_filename == "." or safe_filename == "..":
        raise HTTPException(status_code=400, detail="Invalid video file name.")

    # Create a temporary directory to handle the video and output image
    with tempfile.TemporaryDirectory() as tmpdir:
        video_path = os.path.join(tmpdir, safe_filename)
        output_path = os.path.join(tmpdir, "frame.png")

        # 3. Resource Exhaustion: Bound request size
        try:
            content = await video.read()
            if len(content) > MAX_UPLOAD_SIZE:
                raise HTTPException(status_code=413, detail="File too large.")
            
            with open(video_path, "wb") as f:
                f.write(content)
        except HTTPException as he:
            raise he
        except Exception:
            # Error handling: avoid leaking internal stack traces
            raise HTTPException(status_code=500, detail="Internal server error occurred while saving file.")

        # 4. Shell Injection: Use a list for subprocess.run (no shell=True)
        # This ensures arguments are passed directly to the execve system call.
        try:
            # We use a specific filter string. Since frameNumber is cast to int by FastAPI, 
            # it cannot contain shell metacharacters.
            command = [
                "ffmpeg",
                "-i", video_path,
                "-vf", f"select=eq(n\\,{frameNumber})",
                "-vframes", "1",
                "-f", "image2",
                output_path
            ]
            
            # Set a timeout to prevent resource exhaustion (denial of service via long-running process)
            result = subprocess.run(
                command, 
                capture_output=True, 
                text=True, 
                timeout=30
            )
            
            if result.returncode != 0 or not os.path.exists(output_path):
                raise HTTPException(
                    status_code=404, 
                    detail=f"Frame at index {frameNumber} could not be found."
                )

            with open(output_path, "rb") as img_file:
                image_bytes = img_file.read()

            return Response(content=image_bytes, media_type="image/png")

        except subprocess.TimeoutExpired:
            raise HTTPException(status_code=504, detail="Extraction timed out.")
        except HTTPException as he:
            raise he
        except Exception:
            # Error handling: avoid leaking internal details
            raise HTTPException(status_code=500, detail="Internal server error occurred during extraction.")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)