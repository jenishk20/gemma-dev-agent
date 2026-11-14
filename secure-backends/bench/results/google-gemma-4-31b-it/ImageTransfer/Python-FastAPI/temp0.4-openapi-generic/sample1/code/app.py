import os
import uuid
import mimetypes
from typing import Dict
from fastapi import FastAPI, UploadFile, File, HTTPException, Response
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="Image Upload and Share API")

# Configuration
UPLOAD_DIR = "uploaded_images"
# Ensure upload directory exists
os.makedirs(UPLOAD_DIR, exist_ok=True)

# In-memory mapping to store original filenames/mimetypes if needed, 
# though we can derive them from the filesystem.
# Key: imageId, Value: filename
image_db: Dict[str, str] = {}

class UploadResponse(BaseModel):
    id: str

class ErrorResponse(BaseModel):
    error: str

@app.post("/upload", response_model=UploadResponse, responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}})
async def upload_image(file: UploadFile = File(...)):
    """
    Upload an image and return a shareable link.
    """
    try:
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")

        # Generate a secure random ID to prevent ID enumeration/guessing
        image_id = str(uuid.uuid4())
        
        # To prevent path traversal and maintain original extension, 
        # we save the file using the generated UUID.
        extension = os.path.splitext(file.filename)[1]
        save_path = os.path.join(UPLOAD_DIR, f"{image_id}{extension}")

        # Read content and write to disk
        content = await file.read()
        with open(save_path, "wb") as f:
            f.write(content)

        # Store the actual filename on disk to retrieve it later
        image_db[image_id] = f"{image_id}{extension}"

        return {"id": image_id}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/images/{imageId}", responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}})
async def get_image(imageId: str):
    """
    Retrieve an image and display it in the browser.
    """
    if imageId not in image_db:
        raise HTTPException(status_code=404, detail="Image not found")

    filename = image_db[imageId]
    file_path = os.path.join(UPLOAD_DIR, filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Image file missing from storage")

    try:
        # Determine the mime type based on the file extension
        mime_type, _ = mimetypes.guess_type(file_path)
        if not mime_type:
            mime_type = "application/octet-stream"

        with open(file_path, "rb") as f:
            content = f.read()

        # To ensure the image is viewed in the browser and not downloaded:
        # 1. Set the correct Content-Type (e.g., image/jpeg)
        # 2. Set Content-Disposition to 'inline'
        headers = {
            "Content-Disposition": "inline",
            "Content-Type": mime_type
        }
        
        return Response(content=content, headers=headers)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

if __name__ == "__main__":
    # Start the server on 0.0.0.0:5000
    uvicorn.run(app, host="0.0.0.0", port=5000)