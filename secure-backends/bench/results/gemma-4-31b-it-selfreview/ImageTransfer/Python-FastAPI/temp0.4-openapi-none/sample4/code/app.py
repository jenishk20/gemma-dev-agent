import os
import uuid
import mimetypes
from typing import Dict
from fastapi import FastAPI, UploadFile, File, HTTPException, Response, Request
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="Image Upload and Share API")

# Configuration
UPLOAD_DIR = os.path.abspath("uploaded_images")
# Limit upload size to 10MB to prevent resource exhaustion
MAX_FILE_SIZE = 10 * 1024 * 1024 

if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

# In-memory mapping to store original filenames and mimetypes
image_metadata: Dict[str, dict] = {}

class UploadResponse(BaseModel):
    id: str

class ErrorResponse(BaseModel):
    error: str

@app.post("/upload", response_model=UploadResponse, responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}})
async def upload_image(request: Request, file: UploadFile = File(...)):
    """
    Upload an image. Accept all formats. 
    Allow users to upload images, returning a shareable link.
    """
    try:
        # Resource exhaustion check: basic check on content-length header
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail="File too large")

        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")

        # Generate a unique ID for the image (UUID4 is cryptographically secure for IDs)
        image_id = str(uuid.uuid4())
        
        # Determine the content type
        content_type = file.content_type
        if not content_type:
            content_type, _ = mimetypes.guess_type(file.filename)
            content_type = content_type or "application/octet-stream"

        # Read content and check size again to prevent memory exhaustion
        content = await file.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail="File too large")

        # Path Traversal Prevention: 
        # We do NOT use the user-provided filename for the storage path.
        # We use the generated UUID, which is controlled by the server.
        file_path = os.path.join(UPLOAD_DIR, image_id)
        
        with open(file_path, "wb") as f:
            f.write(content)

        # Sanitize filename for the metadata to prevent header injection/XSS when served
        # Strip CR/LF and limit length
        safe_filename = "".join(c for c in file.filename if c not in "\r\n").strip()[:255]

        image_metadata[image_id] = {
            "mimetype": content_type,
            "filename": safe_filename
        }

        return UploadResponse(id=image_id)
    except HTTPException as he:
        raise he
    except Exception:
        # Generic error to avoid leaking internal stack traces
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/images/{imageId}", responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}})
async def get_image(imageId: str):
    """
    Share an image. Look at an image in the browser.
    """
    # Path Traversal Prevention:
    # 1. Validate that imageId is a valid UUID string to ensure no '..' or '/' are present.
    try:
        uuid.UUID(imageId)
    except ValueError:
        # If it's not a valid UUID, it cannot be a valid key in our metadata or a safe filename
        raise HTTPException(status_code=404, detail="Image not found")

    if imageId not in image_metadata:
        raise HTTPException(status_code=404, detail="Image not found")

    # Resolve absolute path and verify it is within UPLOAD_DIR
    file_path = os.path.abspath(os.path.join(UPLOAD_DIR, imageId))
    if not file_path.startswith(UPLOAD_DIR):
        raise HTTPException(status_code=400, detail="Invalid path")
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Image not found")

    try:
        with open(file_path, "rb") as f:
            content = f.read()
        
        mimetype = image_metadata[imageId]["mimetype"]
        filename = image_metadata[imageId]["filename"]
        
        # Ensure the image is viewable in the browser and not recommended for download.
        # We use the sanitized filename in the header.
        return Response(
            content=content, 
            media_type=mimetype,
            headers={"Content-Disposition": f"inline; filename=\"{filename}\""}
        )
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)