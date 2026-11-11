import os
import uvicorn
from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel

app = FastAPI(title="SongDownloader")

# Define the absolute path for the songs directory and resolve it to handle any symlinks
SONGS_DIRECTORY = os.path.realpath("/var/songs")

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
        raise HTTPException(status_code=400, detail="Invalid input")

    # 2. Path Traversal: Reject absolute paths and directory traversal sequences
    if not filename or ".." in filename or filename.startswith("/") or filename.startswith("\\"):
        raise HTTPException(status_code=400, detail="Invalid input")

    # Construct the full path and resolve it to eliminate any remaining '..' or symlink tricks
    # os.path.join is used, but we must verify the resulting path is still within SONGS_DIRECTORY
    unsafe_path = os.path.join(SONGS_DIRECTORY, filename)
    safe_path = os.path.realpath(unsafe_path)

    # Ensure the resolved path starts with the resolved SONGS_DIRECTORY path
    if not safe_path.startswith(SONGS_DIRECTORY + os.sep) and safe_path != SONGS_DIRECTORY:
        raise HTTPException(status_code=400, detail="Invalid input")

    # 3. File Existence: Check if the file exists and is a file (not a directory)
    if not os.path.isfile(safe_path):
        raise HTTPException(status_code=404, detail="File does not exist")

    try:
        # 4. Resource Exhaustion: Limit the size of the file being read into memory
        # Since the prompt forbids streaming responses, we must read the file.
        # We check the size first to prevent MemoryError/DoS.
        file_size = os.path.getsize(safe_path)
        if file_size > 100 * 1024 * 1024:  # Limit to 100MB
            raise HTTPException(status_code=400, detail="File too large")

        with open(safe_path, "rb") as f:
            content = f.read()
        
        return Response(
            content=content, 
            media_type="audio/mpeg"
        )
    except PermissionError:
        # Error handling: Do not leak internal system details (like "Permission Denied")
        raise HTTPException(status_code=404, detail="File does not exist")
    except Exception:
        # Generic catch-all to prevent stack trace leakage
        raise HTTPException(status_code=400, detail="Invalid input")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)