import os
import subprocess
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
    """
    Extracts a specific frame from an uploaded video using ffmpeg.
    """
    # Create a temporary directory to handle the files
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, videoFileName)
        output_path = os.path.join(tmpdir, "frame.png")

        # Save the uploaded video to the temporary path
        try:
            with open(input_path, "wb") as buffer:
                content = await video.read()
                buffer.write(content)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Could not save uploaded file: {str(e)}")

        # ffmpeg command to extract a specific frame
        # -i: input file
        # -vf "select=eq(n,X)": select frame index X
        # -vframes 1: output exactly one frame
        # -f image2: force image format
        cmd = [
            "ffmpeg",
            "-i", input_path,
            "-vf", f"select=eq(n,{frameNumber})",
            "-vframes", "1",
            "-f", "image2",
            output_path
        ]

        try:
            # Run ffmpeg. stderr is captured to check for errors.
            process = subprocess.run(cmd, capture_output=True, text=True)
            
            # If ffmpeg failed or the output file wasn't created, the frame index might be out of range
            if process.returncode != 0 or not os.path.exists(output_path):
                raise HTTPException(
                    status_code=404, 
                    detail=f"Frame at index {frameNumber} could not be found."
                )

            # Read the extracted frame into memory
            with open(output_path, "rb") as img_file:
                image_bytes = img_file.read()

            return Response(content=image_bytes, media_type="image/png")

        except subprocess.CalledProcessError:
            raise HTTPException(
                status_code=404, 
                detail=f"Frame at index {frameNumber} could not be found."
            )
        except Exception as e:
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    # Start the server on 0.0.0.0:5000
    uvicorn.run(app, host="0.0.0.0", port=5000)