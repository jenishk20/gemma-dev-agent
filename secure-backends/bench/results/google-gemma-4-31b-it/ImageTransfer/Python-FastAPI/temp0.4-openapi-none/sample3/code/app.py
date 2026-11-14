import os
import uuid
import shutil
from typing import Dict
from fastapi import FastAPI, UploadFile, File, HTTPException, Response
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="Image Upload and Share API")

# Configuration
UPLOAD_DIR = "uploaded_images"
# Store mapping of imageId to (filename, mimetype)
# In a production app, this would be a database.
db: Dict[str, tuple] = {}

# Ensure upload directory exists
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

class UploadResponse(BaseModel):
    id: str

class ErrorResponse(BaseModel):
    error: str

@app.post("/upload", response_model=UploadResponse)
async def upload_image(file: UploadFile = File(...)):
    """
    Upload an image. Accept all formats.
    """
    try:
        # Generate a unique ID for the image
        image_id = str(uuid.uuid4())
        
        # We keep the original extension to help with file system storage, 
        # but we track the content_type for the response.
        extension = os.path.splitext(file.filename)[1]
        save_path = os.path.join(UPLOAD_DIR, f"{image_id}{extension}")
        
        # Read content and save to disk
        content = await file.read()
        with open(save_path, "wb") as f:
            f.write(content)
            
        # Store metadata: (full_path, mimetype)
        db[image_id] = (save_path, file.content_type)
        
        return UploadResponse(id=image_id)
    except Exception as e:
        # Log error here in real scenario
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/images/{imageId}")
async def get_image(imageId: str):
    """
    Share an image. Look at an image in the browser.
    """
    if imageId not in db:
        raise HTTPException(status_code=404, detail="Image not found")
    
    file_path, mime_type = db[imageId]
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Image file missing from storage")

    try:
        with open(file_path, "rb") as f:
            content = f.read()
        
        # To ensure the image is viewable in the browser and not recommended for download,
        # we set the correct Content-Type and avoid adding 'Content-Disposition: attachment'.
        # 'inline' is the default behavior for images when Content-Type is set.
        return Response(
            content=content, 
            media_type=mime_type,
            headers={"Content-Disposition": "inline"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")

if __name__ == "__main__":
    # Start the server on 0.0.0.0:5000
    uvicorn.run(app, host="0.0.0.0", port=5000)