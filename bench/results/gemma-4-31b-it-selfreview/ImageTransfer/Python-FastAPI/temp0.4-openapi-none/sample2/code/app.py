import os
import uuid
from typing import Dict
from fastapi import FastAPI, UploadFile, File, HTTPException, Response
from fastapi.responses import FileResponse
import uvicorn

app = FastAPI(title="Image Upload and Share API")

# Directory to store uploaded images
UPLOAD_DIR = os.path.abspath("uploaded_images")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# In-memory mapping to track original filenames and mimetypes
image_metadata: Dict[str, Dict[str, str]] = {}

# Resource exhaustion limit: 10MB
MAX_FILE_SIZE = 10 * 1024 * 1024

@app.post("/upload", summary="Upload an image. Accept all formats.")
async def upload_image(file: UploadFile = File(...)):
    """
    Allow users to upload images, returning a shareable link.
    """
    try:
        # Resource exhaustion: Check file size
        # Note: UploadFile.read() reads the whole file into memory.
        content = await file.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail="File too large")

        # Generate a unique ID for the image (UUID4 is cryptographically secure randomness)
        image_id = str(uuid.uuid4())
        
        # Path Traversal Prevention: 
        # We ignore the user-provided filename for the actual disk path.
        # We only extract the extension, validating it contains no path separators.
        filename = file.filename or "image.bin"
        extension = os.path.splitext(filename)[1]
        
        # Sanitize extension to prevent path traversal via extension (e.g., ".jpg/../../etc/passwd")
        # Only allow alphanumeric characters and a single dot.
        clean_ext = "".join(c for c in extension if c.isalnum() or c == '.')
        
        # Construct the path using the generated UUID, ensuring it's inside UPLOAD_DIR
        save_path = os.path.join(UPLOAD_DIR, f"{image_id}{clean_ext}")
        
        # Double check that the resulting path is still within UPLOAD_DIR
        if not os.path.abspath(save_path).startswith(UPLOAD_DIR):
            raise HTTPException(status_code=400, detail="Invalid filename")

        with open(save_path, "wb") as f:
            f.write(content)
        
        # Store metadata
        # Sanitize content_type to prevent header injection (CRLF)
        content_type = file.content_type if file.content_type else "image/octet-stream"
        content_type = "".join(c for c in content_type if c not in '\r\n')

        image_metadata[image_id] = {
            "path": save_path,
            "content_type": content_type
        }
        
        return {"id": image_id}
    except HTTPException as he:
        raise he
    except Exception:
        # Error handling: Return documented 500 without leaking stack traces
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/images/{imageId}", summary="Share an image")
async def share_image(imageId: str):
    """
    Look at an image in the browser.
    """
    # Path Traversal Prevention: 
    # imageId is used as a key in our metadata map, not directly as a path.
    # We validate that the ID exists in our controlled dictionary.
    if imageId not in image_metadata:
        raise HTTPException(status_code=404, detail="Image not found")
    
    meta = image_metadata[imageId]
    file_path = meta["path"]
    
    # Final check to ensure the file exists and is within the allowed directory
    if not os.path.exists(file_path) or not os.path.abspath(file_path).startswith(UPLOAD_DIR):
        raise HTTPException(status_code=404, detail="Image not found")

    try:
        # FileResponse handles the binary stream.
        # We set Content-Disposition to 'inline' to ensure browser viewing.
        return FileResponse(
            path=file_path, 
            media_type=meta["content_type"], 
            filename=None, 
            headers={"Content-Disposition": "inline"}
        )
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)