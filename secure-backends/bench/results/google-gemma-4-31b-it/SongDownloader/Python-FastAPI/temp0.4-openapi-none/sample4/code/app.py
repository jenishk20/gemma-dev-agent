import os
import uvicorn
from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel

app = FastAPI(title="SongDownloader")

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
    if not filename or ".." in filename or filename.startswith("/") or filename.startswith("\\"):
        raise HTTPException(status_code=400, detail="Invalid input")

    file_path = os.path.join(SONGS_DIRECTORY, filename)

    # Check if file exists and is actually a file
    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="File does not exist")

    try:
        with open(file_path, "rb") as f:
            content = f.read()
        
        return Response(
            content=content, 
            media_type="audio/mpeg"
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading file: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)