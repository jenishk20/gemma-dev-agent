import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import uvicorn

app = FastAPI(title="FileSearch", version="1.0.11")

# Define the base data directory
BASE_DATA_DIR = "/data"

class SearchRequest(BaseModel):
    search_content: Optional[str] = Field(None, example="Hello World")
    search_filename: Optional[str] = Field(None, example="file.txt")
    search_dir: Optional[str] = Field(None, example="/songs")

class SearchResponse(BaseModel):
    files: List[str]

def safe_path_resolve(base: str, relative: Optional[str]) -> str:
    """
    Resolves a path and ensures it stays within the BASE_DATA_DIR to prevent 
    Directory Traversal attacks.
    """
    if not relative:
        return base
    
    # Remove leading slash to treat as relative to BASE_DATA_DIR
    rel_path = relative.lstrip('/')
    full_path = os.path.abspath(os.path.join(base, rel_path))
    
    # Ensure the resolved path starts with the absolute path of BASE_DATA_DIR
    if not full_path.startswith(os.path.abspath(base)):
        raise HTTPException(status_code=400, detail="Invalid search directory")
    
    return full_path

@app.post("/search", response_model=SearchResponse)
async def search_files(request: SearchRequest):
    # 1. Resolve the directory to search in
    try:
        target_dir = safe_path_resolve(BASE_DATA_DIR, request.search_dir)
    except HTTPException as e:
        raise e

    if not os.path.exists(target_dir) or not os.path.isdir(target_dir):
        # Return empty list if directory doesn't exist rather than 400, 
        # unless the path resolution failed.
        return SearchResponse(files=[])

    matched_files = []

    # Walk through the directory tree
    for root, dirs, files in os.walk(target_dir):
        for filename in files:
            full_path = os.path.join(root, filename)
            
            # Check Filename Match
            # If search_filename is provided, check if the file starts with it or matches it
            if request.search_filename:
                if not filename.startswith(request.search_filename):
                    continue
            
            # Check Content Match
            # If search_content is provided, read file and check for substring
            if request.search_content:
                try:
                    # We open in binary mode or with errors='ignore' to prevent 
                    # crashes on non-text files (e.g. images, mp3s)
                    with open(full_path, 'rb') as f:
                        content = f.read().decode('utf-8', errors='ignore')
                        if request.search_content not in content:
                            continue
                except (OSError, IOError):
                    # If file cannot be read, skip it
                    continue

            matched_files.append(full_path)

    return SearchResponse(files=matched_files)

if __name__ == "__main__":
    # Start the server on 0.0.0.0:5000
    uvicorn.run(app, host="0.0.0.0", port=5000)