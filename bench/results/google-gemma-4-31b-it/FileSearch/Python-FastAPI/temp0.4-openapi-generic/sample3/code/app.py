import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import uvicorn

app = FastAPI(title="FileSearch", version="1.0.11")

# The base directory where files are stored
BASE_DATA_DIR = "/data"

class SearchRequest(BaseModel):
    search_content: Optional[str] = Field(default=None, example="Hello World")
    search_filename: Optional[str] = Field(default=None, example="file.txt")
    search_dir: Optional[str] = Field(default=None, example="/songs")

class SearchResponse(BaseModel):
    files: List[str]

def safe_join(base, relative):
    """
    Prevents directory traversal attacks by ensuring the resolved path 
    is contained within the BASE_DATA_DIR.
    """
    # Normalize paths to remove '..' and '.'
    # If search_dir starts with '/', we treat it as relative to /data
    rel_path = relative.lstrip('/') if relative else ""
    final_path = os.path.abspath(os.path.join(base, rel_path))
    
    if not final_path.startswith(os.path.abspath(base)):
        raise HTTPException(status_code=400, detail="Invalid search directory")
    
    return final_path

@app.post("/search", response_model=SearchResponse)
async def search_files(request: SearchRequest):
    # Validate and resolve the search directory
    try:
        target_dir = safe_join(BASE_DATA_DIR, request.search_dir)
    except HTTPException as e:
        raise e

    if not os.path.exists(target_dir) or not os.path.isdir(target_dir):
        # If the directory doesn't exist, we return an empty list rather than 404
        # to maintain consistent API behavior for search.
        return SearchResponse(files=[])

    matched_files = []

    # Walk through the directory tree
    for root, dirs, files in os.walk(target_dir):
        for filename in files:
            # 1. Check Filename Match
            # If search_filename is provided, check if it matches the current file
            if request.search_filename:
                if request.search_filename.lower() in filename.lower():
                    matched_files.append(os.path.join(root, filename))
                    continue # Move to next file if filename matched

            # 2. Check Content Match
            # If search_content is provided, read file content
            if request.search_content:
                file_path = os.path.join(root, filename)
                try:
                    # We open in binary mode and decode to handle potential encoding issues
                    # or use 'ignore' to avoid crashing on non-text files.
                    with open(file_path, 'rb') as f:
                        content = f.read().decode('utf-8', errors='ignore')
                        if request.search_content in content:
                            matched_files.append(file_path)
                except (OSError, IOError):
                    # Skip files that cannot be read
                    continue

    # If neither filename nor content was provided, we shouldn't return every file in the system
    if request.search_filename is None and request.search_content is None:
        raise HTTPException(status_code=400, detail="Please provide either search_filename or search_content")

    return SearchResponse(files=matched_files)

if __name__ == "__main__":
    # Start the server on 0.0.0.0:5000
    uvicorn.run(app, host="0.0.0.0", port=5000)