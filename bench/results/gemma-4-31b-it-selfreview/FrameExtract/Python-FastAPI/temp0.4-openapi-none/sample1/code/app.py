import subprocess
import os
import tempfile
import uvicorn
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Response
from typing import Annotated

app = FastAPI(title="FrameExtract")

# Resource exhaustion: Limit the maximum size of the uploaded video (e.g., 100MB)
MAX_UPLOAD_SIZE = 100 * 1024 * 1024 

@app.post("/extract")
async def extract_frame(
    videoFileName: Annotated[str, Form()],
    frameNumber: Annotated[int, Form()],
    video: UploadFile = File(...)
):
    # Path Traversal Prevention: 
    # 1. Reject absolute paths or paths containing '..'
    # 2. Use os.path.basename to ensure we only use the filename, not a path
    safe_filename = os.path.basename(videoFileName)
    if not safe_filename or safe_filename == "." or safe_filename == "..":
        raise HTTPException(status_code=400, detail="Invalid filename provided.")

    # Resource exhaustion: Validate frameNumber is non-negative
    if frameNumber < 0:
        raise HTTPException(status_code=400, detail="Frame number must be non-negative.")

    # Create a temporary directory to handle the files
    with tempfile.TemporaryDirectory() as tmpdir:
        # Resolve paths to ensure they stay inside the temporary directory
        input_path = os.path.join(tmpdir, safe_filename)
        output_path = os.path.join(tmpdir, "frame.png")

        # Save the uploaded video to the temporary path with size check
        try:
            size = 0
            with open(input_path, "wb") as f:
                while chunk := await video.read(1024 * 1024): # Read in 1MB chunks
                    size += len(chunk)
                    if size > MAX_UPLOAD_SIZE:
                        raise HTTPException(status_code=413, detail="File too large.")
                    f.write(chunk)
        except HTTPException as he:
            raise he
        except Exception:
            # Error handling: Return generic error to avoid leaking internal details
            raise HTTPException(status_code=500, detail="An error occurred while saving the uploaded file.")

        # Command Injection Prevention:
        # We use a list for subprocess.run (shell=False by default), which avoids shell interpretation.
        # The frameNumber is cast to int by FastAPI/Pydantic, preventing injection via that variable.
        cmd = [
            "ffmpeg",
            "-i", input_path,
            "-vf", f"select=eq(n\\,{frameNumber})",
            "-vframes", "1",
            "-y",
            output_path
        ]

        try:
            # Resource exhaustion: Add a timeout to prevent ffmpeg from hanging indefinitely
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=30 
            )
            
            # Check if the output file was actually created and has size > 0
            if result.returncode != 0 or not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
                raise HTTPException(
                    status_code=404, 
                    detail=f"Frame at index {frameNumber} could not be found."
                )

            # Read the extracted image and return as PNG response
            with open(output_path, "rb") as img_file:
                image_bytes = img_file.read()
            
            return Response(content=image_bytes, media_type="image/png")

        except subprocess.TimeoutExpired:
            raise HTTPException(status_code=500, detail="Processing timed out.")
        except subprocess.CalledProcessError:
            raise HTTPException(status_code=404, detail=f"Frame at index {frameNumber} could not be found.")
        except Exception as e:
            if isinstance(e, HTTPException):
                raise e
            # Error handling: Prevent leaking stack traces
            raise HTTPException(status_code=500, detail="An internal error occurred during frame extraction.")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)