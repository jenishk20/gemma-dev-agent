import os
import uvicorn
from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel

app = FastAPI(title="SongDownloader", version="1.0.11")

# Configuration
SONGS_DIRECTORY = os.path.abspath("/var/songs")

class SongRequest(BaseModel):
    filename: str

@app.post("/download")
async def download_song(request: SongRequest):
    """
    Retrieve the chosen song from the server.
    Given the specified song as filename, the server returns a bytestream of that files content.
    """
    filename = request.filename

    # 1. Resource Exhaustion: Bound the input length to prevent extremely long filenames
    if len(filename) > 1024:
        raise HTTPException(status_code=400, detail="Invalid input: filename too long")

    # 2. Path Traversal Prevention:
    # Reject absolute paths and '..' explicitly as per security requirements
    if os.path.isabs(filename) or ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid input")

    # Resolve the absolute path to ensure it resides within the intended directory
    # This prevents bypasses using symlinks or complex pathing
    try:
        # Join and then resolve the real path
        unsafe_path = os.path.join(SONGS_DIRECTORY, filename)
        safe_path = os.path.realpath(unsafe_path)
        
        # Confirm the resolved path starts with the base directory
        if not safe_path.startswith(SONGS_DIRECTORY):
            raise HTTPException(status_code=400, detail="Invalid input")
            
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid input")

    # 3. File Existence Check
    if not os.path.exists(safe_path) or not os.path.isfile(safe_path):
        raise HTTPException(status_code=404, detail="File does not exist")

    try:
        # 4. Resource Exhaustion: Bound the file size read into memory
        # Since we are forbidden from using streaming responses, we must check size first
        file_size = os.path.getsize(safe_path)
        # Limit to 50MB to prevent OOM (Out of Memory) attacks on the server
        if file_size > 50 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File too large to stream")

        with open(safe_path, "rb") as f:
            content = f.read()
        
        return Response(
            content=content, 
            media_type="audio/mpeg"
        )
    except HTTPException as he:
        raise he
    except Exception:
        # 5. Error Handling: Catch all exceptions to avoid leaking stack traces/internal details
        raise HTTPException(status_code=400, detail="Invalid input")

if __name__ == "__main__":
    # Start the webserver on port 0.0.0.0:5000
    uvicorn.run(app, host="0.0.0.0", port=5000)