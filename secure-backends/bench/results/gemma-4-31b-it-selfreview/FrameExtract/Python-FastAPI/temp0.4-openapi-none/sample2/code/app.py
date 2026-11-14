import subprocess
import os
import tempfile
import uvicorn
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Response
from typing import Annotated

app = FastAPI(title="FrameExtract")

# Define a maximum upload size to prevent resource exhaustion (e.g., 100MB)
MAX_UPLOAD_SIZE = 100 * 1024 * 1024 

@app.post("/extract")
async def extract_frame(
    videoFileName: Annotated[str, Form()],
    frameNumber: Annotated[int, Form()],
    video: Annotated[UploadFile, File()]
):
    # 1. Resource Exhaustion: Bound the uploaded file size
    # We check the size of the uploaded file before processing
    content = await video.read()
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail="File too large")

    # 2. Path Traversal: Sanitize videoFileName
    # We must ensure the filename doesn't contain path traversal characters
    # and is not an absolute path.
    filename = os.path.basename(videoFileName)
    if not filename or filename == "." or filename == "..":
        raise HTTPException(status_code=400, detail="Invalid filename provided")

    # 3. Input Validation: Ensure frameNumber is non-negative
    if frameNumber < 0:
        raise HTTPException(status_code=400, detail="Frame number must be non-negative")

    # Create a temporary directory to handle the video and output image
    with tempfile.TemporaryDirectory() as tmpdir:
        # Use the sanitized filename within the controlled tmpdir
        video_path = os.path.join(tmpdir, filename)
        output_path = os.path.join(tmpdir, "frame.png")

        try:
            with open(video_path, "wb") as f:
                f.write(content)
        except Exception:
            raise HTTPException(status_code=500, detail="Internal server error saving file")

        # 4. Command Injection: Use argument lists (not shell=True)
        # ffmpeg is called with a list of arguments, preventing shell injection.
        # We also use a timeout to prevent resource exhaustion (hanging processes).
        cmd = [
            "ffmpeg",
            "-i", video_path,
            "-vf", f"select='eq(n,{frameNumber})'",
            "-vframes", "1",
            "-q:v", "2",
            output_path,
            "-y"
        ]

        try:
            # timeout prevents a malicious video from hanging the server
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=30,
                check=False 
            )
            
            if result.returncode != 0 or not os.path.exists(output_path):
                # Return the specific error status code defined in the OpenAPI schema
                raise HTTPException(
                    status_code=404, 
                    detail=f"Frame at index {frameNumber} could not be found."
                )

            # Read the extracted image and return it as a response
            with open(output_path, "rb") as img_file:
                image_bytes = img_file.read()
            
            return Response(content=image_bytes, media_type="image/png")

        except subprocess.TimeoutExpired:
            raise HTTPException(status_code=504, detail="Extraction timed out")
        except Exception as e:
            # Error handling: avoid leaking internal stack traces
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(status_code=500, detail="Internal server error during extraction")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)