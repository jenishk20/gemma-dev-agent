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
    video: Annotated[UploadFile, File()]
):
    # Create a temporary directory to handle the video and output image
    with tempfile.TemporaryDirectory() as tmpdir:
        video_path = os.path.join(tmpdir, videoFileName)
        output_path = os.path.join(tmpdir, "frame.png")

        # Save the uploaded video to the temporary path
        try:
            content = await video.read()
            with open(video_path, "wb") as f:
                f.write(content)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Could not save uploaded file: {str(e)}")

        # Use ffmpeg to extract the specific frame
        # -i: input file
        # -vf "select='eq(n,FRAME_NUMBER)'": filter to select the specific frame index
        # -vframes 1: output exactly one frame
        # -q:v 2: high quality
        cmd = [
            "ffmpeg",
            "-i", video_path,
            "-vf", f"select='eq(n,{frameNumber})'",
            "-vframes", "1",
            "-q:v", "2",
            output_path,
            "-y" # Overwrite output file if it exists
        ]

        try:
            # Run ffmpeg and capture stderr to check for success
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0 or not os.path.exists(output_path):
                # If ffmpeg fails or the file wasn't created, the frame index likely doesn't exist
                raise HTTPException(
                    status_code=404, 
                    detail=f"Frame at index {frameNumber} could not be found."
                )

            # Read the extracted image and return it as a response
            with open(output_path, "rb") as img_file:
                image_bytes = img_file.read()
            
            return Response(content=image_bytes, media_type="image/png")

        except subprocess.SubprocessError:
            raise HTTPException(status_code=500, detail="Internal server error during frame extraction.")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)