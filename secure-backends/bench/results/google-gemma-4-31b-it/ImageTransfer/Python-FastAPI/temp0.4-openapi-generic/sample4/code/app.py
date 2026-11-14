import os
import uuid
import mimetypes
from pathlib import Path
from typing import Dict

from fastapi import FastAPI, UploadFile, File, HTTPException, Response
from pydantic import BaseModel

app = FastAPI(
    title="Image Upload and Share API",
    description="An API for uploading images and generating shareable links.",
    version="1.0.0"
)

# Configuration
UPLOAD_DIR = Path("uploaded_images")
UPLOAD_DIR.mkdir(exist_ok=True)

# In-memory mapping to store original filenames and mimetypes
# In a production app, this would be a database.
image_metadata: Dict[str, Dict[str, str]] = {}

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
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")

        # Generate a unique ID to prevent filename collisions and directory traversal attacks
        image_id = str(uuid.uuid4())
        
        # Determine the content type
        content_type = file.content_type or mimetypes.guess_type(file.filename)[0] or "application/octet-stream"
        
        # Save the file using the UUID as the filename to sanitize input
        file_path = UPLOAD_DIR / image_id
        
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
            
        # Store metadata for retrieval
        image_metadata[image_id] = {
            "mimetype": content_type
        }
        
        return {"id": image_id}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get(
    "/images/{imageId}", 
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Share an image"
)
async def share_image(imageId: str):
    """
    Look at an image in the browser.
    """
    # Security: Ensure imageId is a valid UUID format to prevent path traversal
    try:
        uuid.UUID(imageId)
    except ValueError:
        raise HTTPException(status_code=404, detail="Image not found")

    file_path = UPLOAD_DIR / imageId
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Image not found")

    try:
        # Get the original mimetype
        meta = image_metadata.get(imageId, {})
        mimetype = meta.get("mimetype", "image/jpeg")

        with open(file_path, "rb") as f:
            content = f.read()

        # To ensure the browser views the image instead of downloading it:
        # 1. Set the correct Content-Type
        # 2. Use 'inline' in Content-Disposition
        headers = {
            "Content-Type": mimetype,
            "Content-Disposition": f'inline; filename="{imageId}"'
        }
        
        return Response(content=content, headers=headers)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)