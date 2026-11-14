import os
import uuid
import mimetypes
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException, Response
from fastapi.responses import FileResponse
import uvicorn

app = FastAPI(title="Image Upload and Share API")

# Configuration
UPLOAD_DIR = Path("uploaded_images")
UPLOAD_DIR.mkdir(exist_ok=True)

@app.post("/upload", status_code=200)
async def upload_image(file: UploadFile = File(...)):
    """
    Upload an image. Accept all formats.
    Returns a shareable link via the image ID.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    try:
        # Generate a unique ID to prevent filename collisions and directory traversal
        image_id = str(uuid.uuid4())
        
        # Determine extension from the original filename
        extension = Path(file.filename).suffix
        # Save file with the unique ID to prevent overwriting and hide original filenames
        file_path = UPLOAD_DIR / f"{image_id}{extension}"
        
        # Read content and write to disk
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
            
        return {"id": image_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/images/{imageId}")
async def get_image(imageId: str):
    """
    Share an image. Look at an image in the browser.
    """
    # To prevent directory traversal, we iterate through the upload directory 
    # to find the file that starts with the provided imageId.
    try:
        # Find the file that starts with the imageId in the upload directory
        target_file = None
        for file in UPLOAD_DIR.glob(f"{imageId}.*"):
            target_file = file
            break
        
        if target_file is None or not target_file.is_file():
            raise HTTPException(status_code=404, detail="Image not found")

        # Determine the mimetype to ensure the browser renders it instead of downloading
        mime_type, _ = mimetypes.guess_type(target_file)
        if mime_type is None:
            mime_type = "application/octet-stream"

        # FileResponse handles the content delivery. 
        # By not setting 'Content-Disposition: attachment', the browser will attempt to display it.
        return FileResponse(
            path=target_file, 
            media_type=mime_type,
            filename=None # Ensures it's not treated as a download
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    # Start the server on 0.0.0.0:5000 as requested
    uvicorn.run(app, host="0.0.0.0", port=5000)