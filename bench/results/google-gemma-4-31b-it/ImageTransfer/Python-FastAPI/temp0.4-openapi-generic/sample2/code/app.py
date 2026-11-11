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
os.makedirs(UPLOAD_DIR, exist_ok=True)

# In-memory mapping to store original mime-types for each file
# In a production environment, this would be a database.
image_metadata: Dict[str, str] = {}

class UploadResponse(BaseModel):
    id: str

class ErrorResponse(BaseModel):
    error: str

@app.post(
    "/upload", 
    response_model=UploadResponse, 
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Upload an image. Accept all formats."
)
async def upload_image(file: UploadFile = File(...)):
    """
    Allow users to upload images, returning a shareable link.
    """
    try:
        # Generate a unique ID to prevent filename collisions and directory traversal
        file_id = str(uuid.uuid4())
        
        # Determine the content type
        content_type = file.content_type
        if not content_type:
            # Fallback to guessing based on filename if content_type is missing
            content_type, _ = mimetypes.guess_type(file.filename)
            content_type = content_type or "application/octet-stream"

        # Save the file with the unique ID as the name (no extension to prevent execution)
        file_path = os.path.join(UPLOAD_DIR, file_id)
        
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # Store the mimetype to serve it correctly later
        image_metadata[file_id] = content_type
        
        return UploadResponse(id=file_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get(
    "/images/{imageId}", 
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Share an image"
)
async def get_image(imageId: str):
    """
    Look at an image in the browser.
    """
    # Security: Validate imageId to prevent directory traversal
    # Since we use UUIDs, we check if the ID exists in our metadata map
    if imageId not in image_metadata:
        raise HTTPException(status_code=404, detail="Image not found")

    file_path = os.path.join(UPLOAD_DIR, imageId)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Image not found")

    try:
        with open(file_path, "rb") as f:
            content = f.read()
        
        mime_type = image_metadata[imageId]
        
        # To ensure the image is viewable in the browser and not downloaded:
        # 1. Set the correct Content-Type.
        # 2. Set Content-Disposition to 'inline'.
        headers = {
            "Content-Disposition": f"inline; filename=\"image\"",
            "Content-Type": mime_type
        }
        
        return Response(content=content, headers=headers)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

if __name__ == "__main__":
    # Start the server on 0.0.0.0:5000 as requested
    uvicorn.run(app, host="0.0.0.0", port=5000)