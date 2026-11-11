import subprocess
import os
import tempfile
import uvicorn
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Response
from typing import Annotated

app = FastAPI(title="FrameExtract")

@app.post("/extract")
async def extract_frame(
    videoFileName: Annotated[str, Form()],
    frameNumber: Annotated[int, Form()],
    video: UploadFile = File(...)
):
    # Create a temporary directory to handle the files
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, videoFileName)
        output_path = os.path.join(tmpdir, "frame.png")

        # Save the uploaded video to the temporary path
        try:
            content = await video.read()
            with open(input_path, "wb") as f:
                f.write(content)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Could not save uploaded file: {str(e)}")

        # FFmpeg command to extract a specific frame
        # -i: input file
        # -vf "select=eq(n\,X)": select frame index X (0-indexed)
        # -vframes 1: output only one frame
        # -y: overwrite output file
        cmd = [
            "ffmpeg",
            "-i", input_path,
            "-vf", f"select=eq(n\\,{frameNumber})",
            "-vframes", "1",
            "-y",
            output_path
        ]

        try:
            # Run ffmpeg and capture stderr to check for errors
            result = subprocess.run(cmd, capture_output=True, text=True)
            
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

        except subprocess.CalledProcessError:
            raise HTTPException(status_code=404, detail=f"Frame at index {frameNumber} could not be found.")
        except Exception as e:
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)