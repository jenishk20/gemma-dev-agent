import os
import uuid
import uvicorn
from fastapi import FastAPI, UploadFile, File, HTTPException, Response
from pydantic import BaseModel

app = FastAPI(title="Image Upload and Share API")

# Directory to store uploaded images
UPLOAD_DIR = "uploaded_images"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Simple database to map imageId to filename and mimetype
# In a production environment, this would be a real database
image_db = {}

class UploadResponse(BaseModel):
    id: str

class ErrorResponse(BaseModel):
    error: str

@app.post("/upload", response_model=UploadResponse)
async def upload_image(file: UploadFile = File(...)):
    """
    Allow users to upload images, returning a shareable link.
    """
    try:
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")

        # Generate a unique ID for the image
        image_id = str(uuid.uuid4())
        
        # Store the original content type to preserve it on retrieval
        content_type = file.content_type
        if not content_type:
            content_type = "application/octet-stream"

        # Save the file to disk
        file_path = os.path.join(UPLOAD_DIR, image_id)
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        # Store metadata
        image_db[image_id] = {
            "path": file_path,
            "mimetype": content_type
        }

        return {"id": image_id}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/images/{imageId}")
async def get_image(imageId: str):
    """
    Look at an image in the browser.
    """
    if imageId not in image_db:
        raise HTTPException(status_code=404, detail="Image not found")

    try:
        image_info = image_db[imageId]
        file_path = image_info["path"]
        mimetype = image_info["mimetype"]

        with open(file_path, "rb") as f:
            content = f.read()

        # Use Response instead of FileResponse to avoid streaming and ensure 
        # we control the headers. 
        # Content-Disposition is set to 'inline' to ensure it's viewed in browser, not downloaded.
        return Response(
            content=content, 
            media_type=mimetype, 
            headers={"Content-Disposition": "inline"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)