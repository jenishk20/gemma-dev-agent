import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import uvicorn

app = FastAPI(title="FileSearch", description="An API for checking if a file with given content or name exists on the server", version="1.0.11")

# Base directory where files are stored
BASE_DATA_DIR = os.path.normpath("/data")

class SearchRequest(BaseModel):
    search_content: Optional[str] = Field(default=None, example="Hello World")
    search_filename: Optional[str] = Field(default=None, example="file.txt")
    search_dir: Optional[str] = Field(default=None, example="/songs")

class SearchResponse(BaseModel):
    files: List[str]

@app.post("/search", response_model=SearchResponse)
async def search_files(request: SearchRequest):
    try:
        # 1. Path Traversal Prevention
        # We treat search_dir as a relative path from /data.
        # We explicitly reject paths containing '..' to prevent directory traversal.
        target_dir = BASE_DATA_DIR
        if request.search_dir:
            # Reject any path containing '..' to be strictly secure against traversal
            if ".." in request.search_dir:
                raise HTTPException(status_code=400, detail="Invalid input: path traversal detected")
            
            # Strip leading slash to ensure os.path.join treats it as relative to BASE_DATA_DIR
            rel_path = request.search_dir.lstrip('/')
            target_dir = os.path.join(BASE_DATA_DIR, rel_path)
        
        # Resolve the absolute path and verify it is still within /data
        normalized_target = os.path.normpath(target_dir)
        if not normalized_target.startswith(BASE_DATA_DIR):
            raise HTTPException(status_code=400, detail="Invalid input: path outside allowed directory")

        if not os.path.exists(normalized_target) or not os.path.isdir(normalized_target):
            return SearchResponse(files=[])

        matched_files = []

        # 2. Resource Exhaustion Prevention
        # To prevent DoS via massive directory trees or huge files, we implement limits.
        MAX_FILES_TO_SCAN = 10000 
        MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB limit per file to prevent memory exhaustion
        files_scanned = 0

        for root, dirs, files in os.walk(normalized_target):
            for file in files:
                files_scanned += 1
                if files_scanned > MAX_FILES_TO_SCAN:
                    # Stop scanning if we hit the limit to prevent resource exhaustion
                    break
                
                full_path = os.path.join(root, file)
                
                # Filter by filename if specified
                if request.search_filename:
                    if not file.startswith(request.search_filename):
                        continue
                
                # Filter by content if specified
                if request.search_content:
                    try:
                        # Check file size before reading to prevent memory exhaustion
                        if os.path.getsize(full_path) > MAX_FILE_SIZE:
                            continue
                            
                        with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                            # Read content. Since we checked size, this is safe.
                            if request.search_content not in f.read():
                                continue
                    except (OSError, IOError):
                        # Handle permission errors or disappeared files gracefully
                        continue
                
                matched_files.append(full_path)
            
            if files_scanned > MAX_FILES_TO_SCAN:
                break

        return SearchResponse(files=matched_files)

    except HTTPException as he:
        raise he
    except Exception:
        # Error handling: catch all other exceptions to prevent leaking stack traces
        # Return 400 as per the OpenAPI schema for "Invalid input"
        raise HTTPException(status_code=400, detail="Invalid input")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)