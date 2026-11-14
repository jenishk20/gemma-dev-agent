import os
import uvicorn
from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel

app = FastAPI(title="SongDownloader", version="1.0.11")

# Configuration
SONGS_DIRECTORY = os.path.abspath("/var/songs")

class DownloadRequest(BaseModel):
    filename: str

@app.post("/download")
async def download_song(request: DownloadRequest):
    """
    Retrieve the chosen song from the server.
    Given the specified song as filename, the server returns a bytestream of that files content.
    """
    filename = request.filename

    # 1. Path Traversal Prevention:
    # Reject empty input, absolute paths, or paths containing '..'
    if not filename or os.path.isabs(filename) or ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid input")

    # Resolve the absolute path to ensure it is contained within the SONGS_DIRECTORY
    # os.path.join with a relative filename is safe here because we checked for '..' and isabs()
    try:
        target_path = os.path.abspath(os.path.join(SONGS_DIRECTORY, filename))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid input")

    # Verify the resolved path starts with the intended base directory
    if not target_path.startswith(SONGS_DIRECTORY + os.sep) and target_path != SONGS_DIRECTORY:
        raise HTTPException(status_code=400, detail="Invalid input")

    # 2. File Existence Check
    if not os.path.exists(target_path) or not os.path.isfile(target_path):
        raise HTTPException(status_code=404, detail="File does not exist")

    # 3. Resource Exhaustion Prevention:
    # Limit the maximum file size that can be read into memory to prevent OOM (Out of Memory)
    # Setting a reasonable limit for an mp3 file (e.g., 50MB)
    MAX_FILE_SIZE = 50 * 1024 * 1024 
    try:
        file_size = os.path.getsize(target_path)
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail="File too large")
    except OSError:
        raise HTTPException(status_code=400, detail="Invalid input")

    try:
        # Read the file content
        with open(target_path, mode="rb") as f:
            content = f.read()
        
        return Response(content=content, media_type="audio/mpeg")
    except Exception:
        # Generic error handling to avoid leaking internal system details/stack traces
        raise HTTPException(status_code=400, detail="Invalid input")

if __name__ == "__main__":
    # Start the webserver on port 0.0.0.0:5000
    uvicorn.run(app, host="0.0.0.0", port=5000)