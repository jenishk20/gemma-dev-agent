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

    # 1. Validate input is not empty and does not contain path traversal sequences
    # Reject absolute paths and '..' as per security requirements
    if not filename or ".." in filename or filename.startswith("/") or filename.startswith("\\"):
        raise HTTPException(status_code=400, detail="Invalid input")

    # 2. Resolve the absolute path and confirm it stays inside the allowed directory
    # This prevents bypasses using symlinks or complex pathing
    try:
        # Join the base directory with the filename
        unsafe_path = os.path.join(SONGS_DIRECTORY, filename)
        # Resolve the real path to handle any potential symlinks or normalization
        safe_path = os.path.realpath(unsafe_path)
        
        # Ensure the resolved path starts with the base directory path
        if not safe_path.startswith(SONGS_DIRECTORY + os.sep) and safe_path != SONGS_DIRECTORY:
            raise HTTPException(status_code=400, detail="Invalid input")
            
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid input")

    # 3. Check if file exists and is actually a file (not a directory)
    if not os.path.exists(safe_path) or not os.path.isfile(safe_path):
        raise HTTPException(status_code=404, detail="File does not exist")

    try:
        # 4. Resource Exhaustion: Bound the file size to prevent memory exhaustion
        # Since we are forbidden from using streaming responses, we must check size before reading
        MAX_FILE_SIZE = 50 * 1024 * 1024  # Limit to 50MB to prevent OOM
        file_size = os.path.getsize(safe_path)
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail="File too large")

        with open(safe_path, "rb") as f:
            content = f.read()
        
        return Response(
            content=content, 
            media_type="audio/mpeg"
        )
    except HTTPException as he:
        raise he
    except Exception:
        # 5. Error handling: Catch all exceptions and return documented status codes 
        # without leaking internal stack traces or system details.
        raise HTTPException(status_code=400, detail="Invalid input")

if __name__ == "__main__":
    # Start the webserver on port 0.0.0.0:5000
    uvicorn.run(app, host="0.0.0.0", port=5000)