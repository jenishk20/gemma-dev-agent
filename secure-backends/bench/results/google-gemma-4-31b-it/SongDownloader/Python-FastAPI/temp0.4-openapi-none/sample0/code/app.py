import os
import uvicorn
from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel

app = FastAPI(title="SongDownloader", version="1.0.11")

# Configuration
SONGS_DIRECTORY = "/var/songs"

class SongRequest(BaseModel):
    filename: str

@app.post("/download")
async def download_song(request: SongRequest):
    """
    Retrieve the chosen song from the server.
    Given the specified song as filename, the server returns a bytestream of that files content.
    """
    # Basic input validation to prevent directory traversal attacks
    filename = request.filename
    if not filename or ".." in filename or filename.startswith("/"):
        raise HTTPException(status_code=400, detail="Invalid input: filename contains illegal characters")

    file_path = os.path.join(SONGS_DIRECTORY, filename)

    # Check if file exists and is actually a file
    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="File does not exist")

    try:
        # Read the entire file into memory as requested (Do not use streaming responses)
        with open(file_path, "rb") as f:
            content = f.read()
        
        return Response(
            content=content, 
            media_type="audio/mpeg"
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"An error occurred while reading the file: {str(e)}")

if __name__ == "__main__":
    # Start the webserver on port 0.0.0.0:5000
    uvicorn.run(app, host="0.0.0.0", port=5000)