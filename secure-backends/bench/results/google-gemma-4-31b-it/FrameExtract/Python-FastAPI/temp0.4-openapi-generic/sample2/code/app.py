import os
import subprocess
import tempfile
import shutil
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
    # Create a temporary directory to handle files securely
    with tempfile.TemporaryDirectory() as tmpdir:
        # Sanitize the filename to prevent path traversal attacks
        # We use os.path.basename to ensure we aren't writing outside the tmpdir
        safe_video_name = os.path.basename(videoFileName)
        video_path = os.path.join(tmpdir, safe_video_name)
        output_path = os.path.join(tmpdir, "frame.png")

        # Save the uploaded video to the temporary directory
        try:
            with open(video_path, "wb") as buffer:
                shutil.copyfileobj(video.file, buffer)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Could not save uploaded file: {str(e)}")

        # FFmpeg command to extract a specific frame
        # -i: input file
        # -vf "select=eq(n\,frame_number)": filter to select the specific frame index
        # -vframes 1: output exactly one frame
        # -f image2: output format as image
        try:
            # We use a list for subprocess.run to avoid shell injection vulnerabilities
            cmd = [
                "ffmpeg",
                "-i", video_path,
                "-vf", f"select=eq(n\\,{frameNumber})",
                "-vframes", "1",
                "-f", "image2",
                "-y", # Overwrite output file if it exists
                output_path
            ]
            
            # Run ffmpeg. stderr is captured to check for errors.
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                # If ffmpeg failed, it might be because the frame index is out of bounds
                raise HTTPException(
                    status_code=404, 
                    detail=f"Frame at index {frameNumber} could not be found."
                )

            # Verify the output file was actually created and has content
            if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
                raise HTTPException(
                    status_code=404, 
                    detail=f"Frame at index {frameNumber} could not be found."
                )

            # Read the extracted image into memory
            with open(output_path, "rb") as image_file:
                image_bytes = image_file.read()

            return Response(content=image_bytes, media_type="image/png")

        except subprocess.SubprocessError:
            raise HTTPException(status_code=500, detail="Internal error processing video.")
        except HTTPException as he:
            raise he
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    # Start the server on 0.0.0.0:5000 as requested
    uvicorn.run(app, host="0.0.0.0", port=5000)