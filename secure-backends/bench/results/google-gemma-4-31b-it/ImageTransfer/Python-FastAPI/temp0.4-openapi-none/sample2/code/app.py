import os
import uuid
import shutil
from typing import Dict
from fastapi import FastAPI, UploadFile, File, HTTPException, Response
from fastapi.responses import FileResponse
import uvicorn

app = FastAPI(title="Image Upload and Share API")

# Directory to store uploaded images
UPLOAD_DIR = "uploaded_images"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# In-memory mapping to track original filenames and mimetypes
# In a production app, this would be a database.
image_metadata: Dict[str, Dict[str, str]] = {}

@app.post("/upload", summary="Upload an image. Accept all formats.")
async def upload_image(file: UploadFile = File(...)):
    """
    Allow users to upload images, returning a shareable link.
    """
    try:
        # Generate a unique ID for the image
        image_id = str(uuid.uuid4())
        
        # Preserve the original extension to help with mimetype detection
        extension = os.path.splitext(file.filename)[1]
        save_path = os.path.join(UPLOAD_DIR, f"{image_id}{extension}")
        
        # Read content and save to disk
        content = await file.read()
        with open(save_path, "wb") as f:
            f.write(content)
        
        # Store metadata
        image_metadata[image_id] = {
            "path": save_path,
            "content_type": file.content_type if file.content_type else "image/octet-stream"
        }
        
        return {"id": image_id}
    except Exception as e:
        # Handle internal server errors or bad requests
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/images/{imageId}", summary="Share an image")
async def share_image(imageId: str):
    """
    Look at an image in the browser.
    """
    if imageId not in image_metadata:
        raise HTTPException(status_code=404, detail="Image not found")
    
    meta = image_metadata[imageId]
    file_path = meta["path"]
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Image file missing from storage")

    # FileResponse is used here. To ensure it is viewable in browser 
    # and not recommended for download, we set the Content-Disposition to 'inline'.
    # We also pass the original mimetype.
    return FileResponse(
        path=file_path, 
        media_type=meta["content_type"], 
        filename=None, # Setting filename to None prevents Content-Disposition: attachment
        headers={"Content-Disposition": "inline"}
    )

if __name__ == "__main__":
    # Start the webserver on port 0.0.0.0:5000
    uvicorn.run(app, host="0.0.0.0", port=5000)