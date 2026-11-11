import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel, Field

app = FastAPI(title="SongDownloader", description="A simple webapp API for providing the songs stored on this server")

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
    # Security: Prevent Path Traversal attacks
    # We ensure the filename does not contain directory separators and is treated as a base name
    filename = os.path.basename(request.filename)
    if not filename or filename == "." or filename == "..":
        raise HTTPException(status_code=400, detail="Invalid input: filename is required and must be valid")

    file_path = SONGS_DIRECTORY / filename

    # Verify the file exists and is actually a file (not a directory)
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File does not exist")

    try:
        # Requirement: "Do not use streaming responses"
        # We read the file content into memory and return it as a standard Response
        content = file_path.read_bytes()
        return Response(
            content=content, 
            media_type="audio/mpeg"
        )
    except Exception as e:
        # Generic error for unexpected filesystem issues
        raise HTTPException(status_code=400, detail="An error occurred while retrieving the file")

if __name__ == "__main__":
    import uvicorn
    # Start the webserver on port 0.0.0.0:5000 as requested
    uvicorn.run(app, host="0.0.0.0", port=5000)