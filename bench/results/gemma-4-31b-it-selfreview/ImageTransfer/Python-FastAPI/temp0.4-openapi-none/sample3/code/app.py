import os
import uuid
from typing import Dict
from fastapi import FastAPI, UploadFile, File, HTTPException, Response, Request
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="Image Upload and Share API")

# Configuration
UPLOAD_DIR = os.path.abspath("uploaded_images")
# Max upload size: 10MB to prevent resource exhaustion
MAX_FILE_SIZE = 10 * 1024 * 1024 

# Store mapping of imageId to (filename, mimetype)
db: Dict[str, tuple] = {}

# Ensure upload directory exists
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

class UploadResponse(BaseModel):
    id: str

class ErrorResponse(BaseModel):
    error: str

@app.post("/upload", response_model=UploadResponse)
async def upload_image(request: Request, file: UploadFile = File(...)):
    """
    Upload an image. Accept all formats.
    """
    try:
        # Resource exhaustion check: Bound request size
        # We check the content-length header first
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail="File too large")

        # Generate a unique ID for the image (UUID4 is cryptographically secure)
        image_id = str(uuid.uuid4())
        
        # Security: We do NOT use the user-provided filename for the path.
        # We only extract the extension and validate it.
        original_filename = file.filename or ""
        extension = os.path.splitext(original_filename)[1]
        
        # Sanitize extension: allow only alphanumeric and a dot, limit length
        # This prevents path traversal or weird filesystem injections
        safe_ext = "".join(c for c in extension if c.isalnum() or c == '.').lower()
        if len(safe_ext) > 10:
            safe_ext = ""

        # The file is saved using the UUID as the filename, completely ignoring 
        # the user-supplied filename for the actual disk write.
        save_filename = f"{image_id}{safe_ext}"
        save_path = os.path.join(UPLOAD_DIR, save_filename)
        
        # Final path traversal check: ensure the resolved path is inside UPLOAD_DIR
        if not os.path.abspath(save_path).startswith(UPLOAD_DIR):
            raise HTTPException(status_code=400, detail="Invalid path")

        # Read content and save to disk with size limit check
        content = await file.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail="File too large")
            
        with open(save_path, "wb") as f:
            f.write(content)
            
        # Store metadata: (full_path, mimetype)
        # We sanitize the mimetype to prevent HTTP header injection (CRLF)
        mimetype = file.content_type or "application/octet-stream"
        sanitized_mimetype = "".join(c for c in mimetype if c not in "\r\n")
        
        db[image_id] = (save_path, sanitized_mimetype)
        
        return UploadResponse(id=image_id)
    except HTTPException as he:
        raise he
    except Exception:
        # Error handling: catch all and return documented 500 without leaking stack traces
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/images/{imageId}")
async def get_image(imageId: str):
    """
    Share an image. Look at an image in the browser.
    """
    # Security: imageId is validated as a key in our internal map.
    # Since we generate the UUIDs ourselves and don't let users set the ID,
    # this prevents path traversal via the imageId parameter.
    if imageId not in db:
        raise HTTPException(status_code=404, detail="Image not found")
    
    file_path, mime_type = db[imageId]
    
    # Verify the file still exists and is within the allowed directory
    if not os.path.exists(file_path) or not os.path.abspath(file_path).startswith(UPLOAD_DIR):
        raise HTTPException(status_code=404, detail="Image not found")

    try:
        with open(file_path, "rb") as f:
            content = f.read()
        
        # Return the image with the preserved mimetype.
        # Content-Disposition: inline ensures it's viewed in browser.
        return Response(
            content=content, 
            media_type=mime_type,
            headers={"Content-Disposition": "inline"}
        )
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)