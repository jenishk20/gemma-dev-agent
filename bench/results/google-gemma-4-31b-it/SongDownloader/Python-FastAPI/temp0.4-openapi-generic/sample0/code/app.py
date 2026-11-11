import os
from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel, Field
import uvicorn

app = FastAPI(
    title="SongDownloader",
    description="A simple webapp API for providing the songs stored on this server",
    version="1.0.11"
)

# Configuration
SONGS_DIRECTORY = "/var/songs"

class SongRequest(BaseModel):
    filename: str = Field(..., example="peters_mixtape.mp3")

@app.post("/download", responses={200: {"content": {"audio/mpeg": {}}}, 404: {}, 400: {}})
async def download_song(request: SongRequest):
    """
    Given the specified song as filename, the server returns a bytestream of that files content
    """
    # Security: Prevent Path Traversal attacks
    # Extract only the basename to ensure the user cannot use '../' to access other directories
    safe_filename = os.path.basename(request.filename)
    
    if not safe_filename or safe_filename == request.filename and (".." in request.filename or "/" in request.filename or "\\" in request.filename):
        # While os.path.basename handles most, we explicitly validate to be safe
        raise HTTPException(status_code=400, detail="Invalid input: filename contains illegal characters")

    file_path = os.path.join(SONGS_DIRECTORY, safe_filename)

    # Check if file exists and is actually a file
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="File does not exist")

    try:
        # Read the file content into memory as requested (Do not use streaming responses)
        with open(file_path, mode="rb") as f:
            content = f.read()
        
        return Response(content=content, media_type="audio/mpeg")
    except Exception as e:
        # Log the error internally and return a 400 or 500
        raise HTTPException(status_code=400, detail="An error occurred while retrieving the file")

if __name__ == "__main__":
    # Start the server on 0.0.0.0:5000
    uvicorn.run(app, host="0.0.0.0", port=5000)