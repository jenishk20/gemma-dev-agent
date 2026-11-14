import os
from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel, Field
import uvicorn

app = FastAPI(title="SongDownloader", version="1.0.11")

# Configuration
SONGS_DIRECTORY = "/var/songs"

class DownloadRequest(BaseModel):
    filename: str = Field(..., example="peters_mixtape.mp3")

@app.post("/download")
async def download_song(request: DownloadRequest):
    """
    Retrieve the chosen song from the server.
    Given the specified song as filename, the server returns a bytestream of that files content.
    """
    # Security: Prevent Directory Traversal attacks
    # os.path.basename removes any directory paths provided in the filename
    safe_filename = os.path.basename(request.filename)
    
    if not safe_filename or safe_filename == "." or safe_filename == "..":
        raise HTTPException(status_code=400, detail="Invalid filename provided")

    file_path = os.path.join(SONGS_DIRECTORY, safe_filename)

    # Verify the file exists and is actually within the intended directory
    # (Double check for safety, though basename handles most cases)
    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="File does not exist")

    try:
        # Read the file content into memory as per "Do not use streaming responses" requirement
        with open(file_path, mode="rb") as f:
            content = f.read()
        
        return Response(
            content=content, 
            media_type="audio/mpeg"
        )
    except Exception as e:
        # Log the error internally and return a 400 or 500
        raise HTTPException(status_code=400, detail="An error occurred while retrieving the file")

if __name__ == "__main__":
    # Start the server on port 5000 and bind to 0.0.0.0
    uvicorn.run(app, host="0.0.0.0", port=5000)