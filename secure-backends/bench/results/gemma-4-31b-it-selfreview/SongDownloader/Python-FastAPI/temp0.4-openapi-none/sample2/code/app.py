import os
from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="SongDownloader", description="A simple webapp API for providing the songs stored on this server", version="1.0.11")

# Define the absolute path to the songs directory and resolve it to handle symlinks/relative paths
SONGS_DIRECTORY = os.path.abspath("/var/songs")

class SongRequest(BaseModel):
    filename: str

@app.post("/download", responses={200: {"content": {"audio/mpeg": {}}}, 404: {}, 400: {}})
async def download_song(request: SongRequest):
    """
    Given the specified song as filename, the server returns a bytestream of that files content
    """
    filename = request.filename

    # 1. Prevent empty input or excessively large filenames to mitigate resource exhaustion
    if not filename or len(filename) > 255:
        raise HTTPException(status_code=400, detail="Invalid input")

    # 2. Path Traversal Prevention:
    # We join the base directory with the user-provided filename.
    # We then resolve the absolute path to eliminate '..' and symlinks.
    try:
        # Ensure we are joining a filename, not an absolute path
        # os.path.join ignores previous components if the second argument is absolute
        unsafe_path = os.path.join(SONGS_DIRECTORY, filename)
        resolved_path = os.path.abspath(unsafe_path)

        # Verify that the resolved path is still within the SONGS_DIRECTORY
        # commonpath returns the longest common sub-path of the sequences
        if os.path.commonpath([SONGS_DIRECTORY, resolved_path]) != SONGS_DIRECTORY:
            raise HTTPException(status_code=400, detail="Invalid input")
            
    except (ValueError, OSError):
        raise HTTPException(status_code=400, detail="Invalid input")

    # 3. Resource Existence Check
    if not os.path.isfile(resolved_path):
        raise HTTPException(status_code=404, detail="File does not exist")

    # 4. Secure File Reading
    try:
        # We read the file content. Note: For very large files, this could lead to 
        # memory exhaustion, but the prompt explicitly forbids streaming responses.
        with open(resolved_path, "rb") as f:
            content = f.read()
        
        return Response(content=content, media_type="audio/mpeg")
    except Exception:
        # We catch all exceptions and return a generic 400 to avoid leaking internal system details/stack traces
        raise HTTPException(status_code=400, detail="Invalid input")

if __name__ == "__main__":
    # Start the server on 0.0.0.0:5000 as requested
    uvicorn.run(app, host="0.0.0.0", port=5000)