import os
from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="SongDownloader", description="A simple webapp API for providing the songs stored on this server", version="1.0.11")

SONGS_DIRECTORY = "/var/songs"

class SongRequest(BaseModel):
    filename: str

@app.post("/download", responses={200: {"content": {"audio/mpeg": {}}}, 404: {}, 400: {}})
async def download_song(request: SongRequest):
    """
    Given the specified song as filename, the server returns a bytestream of that files content
    """
    # Basic validation to prevent directory traversal attacks
    filename = request.filename
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid input: Filename must be a simple filename without path components.")

    file_path = os.path.join(SONGS_DIRECTORY, filename)

    # Check if the file exists and is actually a file
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="File does not exist")

    try:
        with open(file_path, "rb") as f:
            content = f.read()
        
        return Response(content=content, media_type="audio/mpeg")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not read file: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)