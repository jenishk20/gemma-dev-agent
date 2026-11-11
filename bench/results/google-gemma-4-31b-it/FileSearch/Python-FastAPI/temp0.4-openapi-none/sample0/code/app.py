import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import uvicorn

app = FastAPI(title="FileSearch", description="An API for checking if a file with given content or name exists on the server", version="1.0.11")

# Base directory where files are stored
BASE_DATA_DIR = "/data"

class SearchRequest(BaseModel):
    search_content: Optional[str] = Field(default=None, example="Hello World")
    search_filename: Optional[str] = Field(default=None, example="file.txt")
    search_dir: Optional[str] = Field(default=None, example="/songs")

class SearchResponse(BaseModel):
    files: List[str]

@app.post("/search", response_model=SearchResponse)
async def search_files(request: SearchRequest):
    # Resolve the starting directory
    # If search_dir is provided, we append it to /data. 
    # We must ensure the resulting path is still within /data to prevent directory traversal.
    target_dir = BASE_DATA_DIR
    if request.search_dir:
        # Remove leading slash to treat as relative to /data
        rel_path = request.search_dir.lstrip('/')
        target_dir = os.path.join(BASE_DATA_DIR, rel_path)
    
    # Security check: ensure target_dir is actually inside /data
    normalized_target = os.path.normpath(target_dir)
    if not normalized_target.startswith(os.path.normpath(BASE_DATA_DIR)):
        raise HTTPException(status_code=400, detail="Invalid search directory")

    if not os.path.exists(normalized_target) or not os.path.isdir(normalized_target):
        # If the directory doesn't exist, we return an empty list rather than 400 
        # unless the schema strictly requires a 400 for "Invalid input".
        # Given the prompt, we'll return empty if not found.
        return SearchResponse(files=[])

    matched_files = []

    # Walk through the directory tree
    for root, dirs, files in os.walk(normalized_target):
        for file in files:
            full_path = os.path.join(root, file)
            
            # Filter by filename if specified
            if request.search_filename:
                if not file.startswith(request.search_filename):
                    continue
            
            # Filter by content if specified
            if request.search_content:
                try:
                    # We open in text mode. If it's a binary file, this might fail or 
                    # read incorrectly, but for a general search API, we attempt to read.
                    with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                        if request.search_content not in f.read():
                            continue
                except Exception:
                    # If file cannot be read, skip it
                    continue
            
            matched_files.append(full_path)

    return SearchResponse(files=matched_files)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)