import os
import uuid
import mimetypes
from fastapi import FastAPI, UploadFile, File, HTTPException, Response
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="Image Upload and Share API")

# Directory to store uploaded images
UPLOAD_DIR = "uploaded_images"
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
    Returns a shareable link identifier.
    """
    try:
        # Generate a unique ID for the file
        image_id = str(uuid.uuid4())
        
        # Determine the extension based on the content type
        content_type, extension = mimetypes.guess_type(file.filename)
        if not extension:
            # Fallback extension if cannot be determined
            extension = ".bin"
        
        file_path = os.path.join(UPLOAD_DIR, f"{image_id}{extension}")
        
        # Read content and save to disk
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
            
        return {"id": image_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/images/{imageId}")
async def get_image(imageId: str):
    """
    Share an image. Look at an image in the browser.
    """
    # Search for the file in the upload directory that starts with the imageId
    try:
        found_file = None
        for filename in os.listdir(UPLOAD_DIR):
            if filename.startswith(imageId):
                found_file = os.path.join(UPLOAD_DIR, filename)
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)