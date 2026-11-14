import os
import uuid
import mimetypes
from fastapi import FastAPI, UploadFile, File, HTTPException, Response, Request
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="Image Upload and Share API")

# Directory to store uploaded images
UPLOAD_DIR = os.path.abspath("uploaded_images")
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

# Resource exhaustion: Limit upload size (e.g., 10MB)
MAX_FILE_SIZE = 10 * 1024 * 1024 

class UploadResponse(BaseModel):
    id: str

class ErrorResponse(BaseModel):
    error: str

@app.post("/upload", response_model=UploadResponse)
async def upload_image(file: UploadFile = File(...)):
    """
    Upload an image. Accept all formats.
    Returns a shareable link identifier.
    """
    try:
        # Resource exhaustion: Check file size
        # Note: UploadFile.read() reads into memory, so we check size during read
        content = await file.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail="File too large")

        # Generate a unique ID for the file (cryptographically secure via uuid4)
        image_id = str(uuid.uuid4())
        
        # Determine the extension based on the content type
        # We ignore the user-provided filename for the storage path to prevent path traversal
        content_type, extension = mimetypes.guess_type(file.filename)
        if not extension:
            extension = ".bin"
        
        # Secure path construction: Use a generated UUID, not user input
        filename = f"{image_id}{extension}"
        file_path = os.path.join(UPLOAD_DIR, filename)
        
        # Double check that the resolved path is still within UPLOAD_DIR
        if not os.path.abspath(file_path).startswith(UPLOAD_DIR):
            raise HTTPException(status_code=400, detail="Invalid file path")

        with open(file_path, "wb") as f:
            f.write(content)
            
        return {"id": image_id}
    except HTTPException as he:
        raise he
    except Exception:
        # Error handling: Do not leak internal stack traces
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/images/{imageId}")
async def get_image(imageId: str):
    """
    Share an image. Look at an image in the browser.
    """
    try:
        # Path Traversal Prevention: 
        # 1. Validate that imageId contains only alphanumeric characters/hyphens (UUID format)
        # This prevents '..' or absolute paths from being used to escape the directory.
        if not all(c.isalnum() or c == '-' for c in imageId):
            raise HTTPException(status_code=400, detail="Invalid image ID format")

        found_file = None
        # List files and find the one starting with the validated imageId
        for filename in os.listdir(UPLOAD_DIR):
            if filename.startswith(imageId):
                # Ensure the filename itself doesn't contain traversal characters
                # (Though we control filename creation in /upload, this is defense-in-depth)
                safe_path = os.path.join(UPLOAD_DIR, filename)
                if os.path.abspath(safe_path).startswith(UPLOAD_DIR):
                    found_file = safe_path
                    break
        
        if not found_file:
            raise HTTPException(status_code=404, detail="Image not found")
        
        # Determine the mimetype to ensure it's viewable in browser
        mime_type, _ = mimetypes.guess_type(found_file)
        if not mime_type:
            mime_type = "application/octet-stream"

        with open(found_file, "rb") as f:
            content = f.read()
            
        # Return as a Response. 
        # 'inline' is the default behavior for browsers when Content-Disposition is not set to 'attachment'.
        return Response(
            content=content, 
            media_type=mime_type,
            headers={"Content-Disposition": "inline"}
        )
    except HTTPException as he:
        raise he
    except Exception:
        # Error handling: Do not leak internal stack traces
        raise HTTPException(status_code=500, detail="Internal server error")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)