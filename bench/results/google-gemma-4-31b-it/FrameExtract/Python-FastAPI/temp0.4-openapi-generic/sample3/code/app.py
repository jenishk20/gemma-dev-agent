import os
import subprocess
import tempfile
import shutil
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Response
from fastapi.responses import Response as FastApiResponse

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
        # Sanitize filename to prevent directory traversal attacks
        # We use a generic name inside the tmpdir to be safe
        input_path = os.path.join(tmpdir, "input_video")
        output_path = os.path.join(tmpdir, "frame.png")

        try:
            # Save the uploaded video to the temporary path
            with open(input_path, "wb") as buffer:
                shutil.copyfileobj(video.file, buffer)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Could not save uploaded file: {str(e)}")

        # ffmpeg command to extract a single frame
        # -i: input file
        # -vf "select=eq(n\,X)": filter to select frame X (0-indexed)
        # -vframes 1: output exactly one frame
        # -f image2: force image format
        try:
            process = subprocess.run(
                [
                    "ffmpeg",
                    "-i", input_path,
                    "-vf", f"select=eq(n\\,{frameNumber})",
                    "-vframes", "1",
                    "-f", "image2",
                    output_path
                ],
                capture_output=True,
                text=True,
                check=True
            )
        except subprocess.CalledProcessError as e:
            # If ffmpeg fails, it might be because the frame index is out of bounds
            # or the file is corrupted.
            raise HTTPException(
                status_code=404, 
                detail=f"Frame at index {frameNumber} could not be found."
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Internal server error during extraction: {str(e)}")

        # Check if the output file was actually created and has size > 0
        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            raise HTTPException(
                status_code=404, 
                detail=f"Frame at index {frameNumber} could not be found."
            )

        # Read the image content to return as a response
        with open(output_path, "rb") as image_file:
            image_bytes = image_file.read()

        return Response(content=image_bytes, media_type="image/png")

if __name__ == "__main__":
    import uvicorn
    # Start the server on 0.0.0.0:5000 as requested
    uvicorn.run(app, host="0.0.0.0", port=5000)