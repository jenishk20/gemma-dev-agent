import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel, Field
import uvicorn

app = FastAPI(title="SongDownloader", version="1.0.11")

# Configuration
SONGS_DIRECTORY = Path("/var/songs")

class DownloadRequest(BaseModel):
    filename: str = Field(..., example="peters_mixtape.mp3")

@app.post("/download", summary="Retrieve the chosen song from the server")
async def download_song(request: DownloadRequest):
    """
    Given the specified song as filename, the server returns a bytestream of that files content
    """
    # Security: Prevent Path Traversal attacks
    # We ensure the filename is just a name and not a path, 
    # and we resolve the final path to ensure it stays within the intended directory.
    filename = os.path.basename(request.filename)
    if not filename or filename == "." or filename == "..":
        raise HTTPException(status_code=400, detail="Invalid filename provided")

    file_path = SONGS_DIRECTORY / filename
    
    # Verify the file exists and is actually a file
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File does not exist")

    try:
        # Requirement: "Do not use streaming responses!"
        # We read the entire file into memory and return it as a Response.
        with open(file_path, "rb") as f:
            content = f.read()
        
        return Response(
            content=content, 
            media_type="audio/mpeg"
        )
    except Exception as e:
        # Generic error handling for filesystem permissions or unexpected IO errors
        raise HTTPException(status_code=400, detail="An error occurred while retrieving the file")

if __name__ == "__main__":
    # Start the server on 0.0.0.0:5000 as requested
    uvicorn.run(app, host="0.0.0.0", port=5000)