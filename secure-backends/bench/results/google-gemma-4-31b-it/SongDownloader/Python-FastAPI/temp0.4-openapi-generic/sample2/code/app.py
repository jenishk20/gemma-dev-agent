import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel, Field
import uvicorn

app = FastAPI(title="SongDownloader")

# Configuration
SONGS_DIRECTORY = Path("/var/songs")

class DownloadRequest(BaseModel):
    filename: str = Field(..., example="peters_mixtape.mp3")

@app.post("/download")
async def download_song(request: DownloadRequest):
    """
    Retrieve the chosen song from the server.
    Given the specified song as filename, the server returns a bytestream of that files content.
    """
    # Security: Prevent Directory Traversal attacks
    # We extract only the name of the file to ensure the user cannot 
    # use '../' to access files outside the designated directory.
    safe_filename = os.path.basename(request.filename)
    if not safe_filename or safe_filename == "." or safe_filename == "..":
        raise HTTPException(status_code=400, detail="Invalid filename provided")

    file_path = SONGS_DIRECTORY / safe_filename

    # Check if file exists and is actually a file
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File does not exist")

    try:
        # Read the file content into memory as requested (No streaming responses)
        content = file_path.read_bytes()
        
        # Return as audio/mpeg as per OpenAPI spec
        return Response(
            content=content, 
            media_type="audio/mpeg"
        )
    except Exception as e:
        # Log the error internally and return a 400 or 500
        raise HTTPException(status_code=400, detail="Error reading file")

if __name__ == "__main__":
    # Start the webserver on port 0.0.0.0:5000
    uvicorn.run(app, host="0.0.0.0", port=5000)