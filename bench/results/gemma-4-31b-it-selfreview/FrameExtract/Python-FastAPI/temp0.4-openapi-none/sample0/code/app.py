import subprocess
import os
import tempfile
import uvicorn
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Response

app = FastAPI(title="FrameExtract")

# Resource exhaustion limits
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB limit to prevent disk exhaustion
FFMPEG_TIMEOUT = 30  # Seconds to prevent hanging processes

@app.post("/extract")
async def extract_frame(
    videoFileName: str = Form(...),
    frameNumber: int = Form(...),
    video: UploadFile = File(...)
):
    # 1. Resource Exhaustion: Validate frameNumber is non-negative
    if frameNumber < 0:
        raise HTTPException(
            status_code=404, 
            detail=f"Frame at index {frameNumber} could not be found."
        )

    # Create a temporary directory to handle the files
    with tempfile.TemporaryDirectory() as tmpdir:
        # 2. Path Traversal: 
        # Use os.path.basename to strip any directory components from the user-provided filename.
        # This ensures the file is saved strictly inside the randomly generated tmpdir.
        safe_filename = os.path.basename(video.filename) if video.filename else "upload.tmp"
        input_path = os.path.join(tmpdir, safe_filename)
        output_path = os.path.join(tmpdir, "frame.png")

        # 3. Resource Exhaustion: Bound the uploaded file size
        try:
            size = 0
            with open(input_path, "wb") as f:
                while chunk := await video.read(1024 * 1024):
                    size += len(chunk)
                    if size > MAX_FILE_SIZE:
                        raise HTTPException(status_code=413, detail="File too large")
                    f.write(chunk)
        except HTTPException:
            raise
        except Exception as e:
            # 4. Error Handling: Do not leak internal stack traces
            raise HTTPException(status_code=500, detail="An error occurred while saving the file.")

        # 5. Shell Injection: 
        # We use a list for subprocess.run, which avoids shell=True and prevents 
        # command injection. The frameNumber is cast to int by FastAPI, 
        # ensuring no malicious strings enter the command list.
        cmd = [
            "ffmpeg",
            "-i", input_path,
            "-vf", f"select=eq(n,{frameNumber})",
            "-vframes", "1",
            "-f", "image2",
            output_path
        ]

        try:
            # Added timeout to prevent resource exhaustion (DoS) via malicious video files
            subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                check=True, 
                timeout=FFMPEG_TIMEOUT
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            # Map ffmpeg errors or timeouts to the 404 as per OpenAPI spec for "not found"
            raise HTTPException(
                status_code=404, 
                detail=f"Frame at index {frameNumber} could not be found."
            )
        except Exception:
            raise HTTPException(status_code=500, detail="An internal error occurred during processing.")

        # Final check for output existence
        if not os.path.exists(output_path):
            raise HTTPException(
                status_code=404, 
                detail=f"Frame at index {frameNumber} could not be found."
            )

        # Read the image and return it as a response
        try:
            with open(output_path, "rb") as f:
                image_bytes = f.read()
        except Exception:
            raise HTTPException(status_code=500, detail="Could not read the extracted frame.")

        return Response(content=image_bytes, media_type="image/png")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)