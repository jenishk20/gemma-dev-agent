import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="FileSearch")

# Base directory where files are stored
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
    # We use os.path.normpath to prevent directory traversal attacks (e.g., ../../)
    target_dir = BASE_DATA_DIR
    if request.search_dir:
        target_dir = os.path.join(BASE_DATA_DIR, request.search_dir)
        target_dir = os.path.normpath(target_dir)
        
        # Security check: Ensure the normalized path still starts with /data
        if not target_dir.startswith(BASE_DATA_DIR):
            raise HTTPException(status_code=400, detail="Invalid search_dir: Path must be within /data")

    if not os.path.exists(target_dir) or not os.path.isdir(target_dir):
        raise HTTPException(status_code=400, detail="Search directory does not exist or is not a directory")

    matched_files = []

    try:
        # Walk through the directory tree
        for root, dirs, files in os.walk(target_dir):
            for filename in files:
                full_path = os.path.join(root, filename)
                
                # 1. Check filename match (starts with)
                if request.search_filename:
                    if not filename.startswith(request.search_filename):
                        continue
                
                # 2. Check content match
                if request.search_content:
                    try:
                        # We open in binary mode and search for bytes to avoid encoding crashes 
                        # with non-text files (like .mp3 mentioned in the example)
                        with open(full_path, 'rb') as f:
                            content = f.read()
                            if request.search_content.encode('utf-8') not in content:
                                continue
                    except (OSError, IOError):
                        # Skip files that cannot be read
                        continue
                
                matched_files.append(full_path)
                
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"An error occurred during search: {str(e)}")

    return SearchResponse(files=matched_files)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)