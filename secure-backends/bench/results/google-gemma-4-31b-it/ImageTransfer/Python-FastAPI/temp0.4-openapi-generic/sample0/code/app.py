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
os.makedirs(UPLOAD_DIR, exist_dir=True) if not os.path.exists(UPLOAD_DIR) else None

# Simple in-memory mapping to track original mimetypes
# In a production environment, this would be a database
image_metadata: Dict[str, str] = {}

class UploadResponse(BaseModel):
    id: str

class ErrorResponse(BaseModel):
    error: str

@app.post("/upload", response_model=UploadResponse)
async def upload_image(file: UploadFile = File(...)):
    """
    Upload an image. Accept all formats.
    Returns a shareable link via a unique ID.
    """
    try:
        # Generate a unique ID to prevent filename collisions and directory traversal attacks
        image_id = str(uuid.uuid4())
        
        # Determine the extension based on the uploaded filename
        extension = os.path.splitext(file.filename)[1]
        # Fallback to a generic extension if none provided
        if not extension:
            extension = ".bin"
            
        file_path = os.path.join(UPLOAD_DIR, f"{image_id}{extension}")
        
        # Store the content type to preserve it during retrieval
        content_type = file.content_type or mimetypes.guess_type(file.filename)[0] or "application/octet-stream"
        
        # Read and save the file
        contents = await file.read()
        with open(file_path, "wb") as f:
            f.write(contents)
            
        image_metadata[image_id] = content_type
        
        return {"id": image_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/images/{imageId}")
async def get_image(imageId: str):
    """
    Share an image. Look at an image in the browser.
    """
    # Prevent directory traversal by validating that imageId is a valid UUID string
    # (since we generate them as UUIDs)
    try:
        uuid.UUID(imageId)
    except ValueError:
        raise HTTPException(status_code=404, detail="Image not found")

    # Search for the file associated with this ID in the upload directory
    target_file = None
    for filename in os.listdir(UPLOAD_DIR):
        if filename.startswith(imageId):
            target_file = os.path.join(UPLOAD_DIR, filename)
            break

    if target_file is None or not os.path.exists(target_file):
        raise HTTPException(status_code=404, detail="Image not found")

    try:
        with open(target_file, "rb") as f:
            image_bytes = f.read()
        
        # Retrieve the original mimetype
        content_type = image_metadata.get(imageId, mimetypes.guess_type(target_file)[0] or "application/octet-stream")
        
        # Use Response instead of FileResponse to avoid streaming and control headers
        # Content-Disposition: inline ensures the browser attempts to render it rather than download it
        return Response(
            content=image_bytes, 
            media_type=content_type, 
            headers={"Content-Disposition": "inline"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

if __name__ == "__main__":
    # Create upload directory if it doesn't exist
    if not os.path.exists(UPLOAD_DIR):
        os.makedirs(UPLOAD_DIR)
        
    uvicorn.run(app, host="0.0.0.0", port=5000)