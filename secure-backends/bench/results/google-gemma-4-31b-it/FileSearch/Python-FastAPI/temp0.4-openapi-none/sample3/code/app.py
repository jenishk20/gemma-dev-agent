import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="FileSearch")

# The base directory where files are stored
BASE_DATA_DIR = "/data"

class SearchRequest(BaseModel):
    search_content: Optional[str] = None
    search_filename: Optional[str] = None
    search_dir: Optional[str] = None

class SearchResponse(BaseModel):
    files: List[str]

@app.post("/search", response_model=SearchResponse)
async def search_files(request: SearchRequest):
    # Determine the starting directory
    # If search_dir is provided, join it with BASE_DATA_DIR
    target_dir = BASE_DATA_DIR
    if request.search_dir:
        # Normalize path to prevent directory traversal attacks
        # Ensure the resulting path is still within /data
        requested_path = os.path.normpath(os.path.join(BASE_DATA_DIR, request.search_dir))
        if not requested_path.startswith(BASE_DATA_DIR):
            raise HTTPException(status_code=400, detail="Invalid search_dir: Path must be within /data")
        target_dir = requested_path

    if not os.path.exists(target_dir) or not os.path.isdir(target_dir):
        # If the directory doesn't exist, we return an empty list or 400 based on interpretation
        # The schema suggests 400 for invalid input
        raise HTTPException(status_code=400, detail="The specified search directory does not exist.")

    matched_files = []

    try:
        for root, dirs, files in os.walk(target_dir):
            for file in files:
                full_path = os.path.join(root, file)
                
                # Filter by filename if provided
                if request.search_filename:
                    if not file.startswith(request.search_filename) and file != request.search_filename:
                        continue
                
                # Filter by content if provided
                if request.search_content:
                    try:
                        # We open in binary mode and search for bytes to avoid encoding crashes with non-text files
                        content_bytes = request.search_content.encode('utf-8')
                        with open(full_path, 'rb') as f:
                            # For very large files, this might be slow, but standard library 
                            # doesn't provide a more efficient 'contains' without reading.
                            if content_bytes not in f.read():
                                continue
                    except (OSError, IOError):
                        # Skip files that cannot be read
                        continue
                
                matched_files.append(full_path)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    return SearchResponse(files=matched_files)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)