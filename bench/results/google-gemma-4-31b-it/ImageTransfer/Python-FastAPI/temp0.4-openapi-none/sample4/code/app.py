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
# Ensure the upload directory exists
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

# In-memory mapping to store original filenames and mimetypes
# In a production app, this would be a database.
image_metadata: Dict[str, dict] = {}

class UploadResponse(BaseModel):
    id: str

class ErrorResponse(BaseModel):
    error: str

@app.post("/upload", response_model=UploadResponse, responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}})
async def upload_image(file: UploadFile = File(...)):
    """
    Upload an image. Accept all formats. 
    Allow users to upload images, returning a shareable link.
    """
    try:
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")

        # Generate a unique ID for the image
        image_id = str(uuid.uuid4())
        
        # Determine the content type
        content_type = file.content_type
        if not content_type:
            content_type, _ = mimetypes.guess_type(file.filename)
            content_type = content_type or "application/octet-stream"

        # Save the file to disk
        file_path = os.path.join(UPLOAD_DIR, image_id)
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        # Store metadata
        image_metadata[image_id] = {
            "mimetype": content_type,
            "filename": file.filename
        }

        return UploadResponse(id=image_id)
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/images/{imageId}", responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}})
async def get_image(imageId: str):
    """
    Share an image. Look at an image in the browser.
    """
    if imageId not in image_metadata:
        raise HTTPException(status_code=404, detail="Image not found")

    file_path = os.path.join(UPLOAD_DIR, imageId)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Image file missing from storage")

    try:
        with open(file_path, "rb") as f:
            content = f.read()
        
        mimetype = image_metadata[imageId]["mimetype"]
        
        # To ensure the image is viewable in the browser and not recommended for download:
        # 1. We set the correct Content-Type.
        # 2. We avoid setting 'Content-Disposition: attachment'.
        # 3. 'inline' is the default behavior for browsers when Content-Disposition is not specified 
        #    or set to 'inline'.
        return Response(
            content=content, 
            media_type=mimetype,
            headers={"Content-Disposition": f"inline; filename=\"{image_metadata[imageId]['filename']}\""}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)