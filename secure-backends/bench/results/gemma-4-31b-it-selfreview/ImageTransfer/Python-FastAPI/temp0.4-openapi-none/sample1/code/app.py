import os
import uuid
import uvicorn
from fastapi import FastAPI, UploadFile, File, HTTPException, Response, Request
from pydantic import BaseModel

app = FastAPI(title="Image Upload and Share API")

# Directory to store uploaded images
UPLOAD_DIR = os.path.abspath("uploaded_images")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Simple database to map imageId to filename and mimetype
image_db = {}

# Resource exhaustion: Limit maximum upload size (e.g., 10MB)
MAX_FILE_SIZE = 10 * 1024 * 1024 

class UploadResponse(BaseModel):
    id: str

class ErrorResponse(BaseModel):
    error: str

@app.post("/upload", response_model=UploadResponse)
async def upload_image(request: Request, file: UploadFile = File(...)):
    """
    Allow users to upload images, returning a shareable link.
    """
    try:
        # Resource exhaustion: Check content length header if available
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail="File too large")

        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")

        # Generate a unique ID for the image (UUID4 is cryptographically secure)
        image_id = str(uuid.uuid4())
        
        # Sanitize content type to prevent header injection (strip CR/LF)
        content_type = file.content_type or "application/octet-stream"
        content_type = content_type.replace("\r", "").replace("\n", "")

        # Path Traversal Prevention: 
        # We do NOT use the user-provided filename for the disk path.
        # We use a generated UUID, ensuring the file stays within UPLOAD_DIR.
        file_path = os.path.join(UPLOAD_DIR, image_id)
        
        # Double check that the resolved path is indeed within the UPLOAD_DIR
        if not os.path.abspath(file_path).startswith(UPLOAD_DIR):
            raise HTTPException(status_code=400, detail="Invalid path")

        # Read file in chunks to prevent memory exhaustion for large files
        content = bytearray()
        while chunk := await file.read(8192):
            content.extend(chunk)
            if len(content) > MAX_FILE_SIZE:
                raise HTTPException(status_code=400, detail="File too large")

        with open(file_path, "wb") as f:
            f.write(content)

        # Store metadata
        image_db[image_id] = {
            "path": file_path,
            "mimetype": content_type
        }

        return {"id": image_id}
    except HTTPException as e:
        raise e
    except Exception:
        # Error handling: Return generic 500 without leaking stack traces
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/images/{imageId}")
async def get_image(imageId: str):
    """
    Look at an image in the browser.
    """
    # Path Traversal Prevention: 
    # imageId is used as a key in our map, not directly as a path.
    # We only access files that were explicitly registered in image_db.
    if imageId not in image_db:
        raise HTTPException(status_code=404, detail="Image not found")

    try:
        image_info = image_db[imageId]
        file_path = image_info["path"]
        mimetype = image_info["mimetype"]

        # Final safety check: ensure the file still exists and is within the allowed directory
        if not os.path.exists(file_path) or not os.path.abspath(file_path).startswith(UPLOAD_DIR):
            raise HTTPException(status_code=404, detail="Image not found")

        with open(file_path, "rb") as f:
            content = f.read()

        # Content-Disposition 'inline' ensures browser viewing.
        # Mimetype is sanitized during upload to prevent header injection.
        return Response(
            content=content, 
            media_type=mimetype, 
            headers={"Content-Disposition": "inline"}
        )
    except HTTPException as e:
        raise e
    except Exception:
        # Error handling: Return generic 500 without leaking stack traces
        raise HTTPException(status_code=500, detail="Internal server error")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)