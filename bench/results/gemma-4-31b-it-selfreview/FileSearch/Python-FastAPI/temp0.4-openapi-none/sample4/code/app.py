import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="FileSearch")

# Base directory where files are stored
BASE_DATA_DIR = "/data"
# Limit the amount of data read from a file to prevent resource exhaustion (DoS)
MAX_FILE_READ_SIZE = 10 * 1024 * 1024  # 10MB limit per file

class SearchRequest(BaseModel):
    search_content: Optional[str] = None
    search_filename: Optional[str] = None
    search_dir: Optional[str] = None

class SearchResponse(BaseModel):
    files: List[str]

@app.post("/search", response_model=SearchResponse)
async def search_files(request: SearchRequest):
    # --- Path Traversal Prevention ---
    # 1. Start with the base directory
    target_dir = BASE_DATA_DIR
    
    if request.search_dir:
        # Reject absolute paths to prevent escaping the base directory via root
        if os.path.isabs(request.search_dir):
            raise HTTPException(status_code=400, detail="Invalid input: absolute paths are not allowed in search_dir")
        
        # Join and normalize to resolve '..' and '.'
        # os.path.join handles relative paths. os.path.normpath cleans them.
        combined_path = os.path.join(BASE_DATA_DIR, request.search_dir)
        normalized_path = os.path.normpath(combined_path)
        
        # Verify the resulting path is still within the BASE_DATA_DIR
        # commonpath returns the longest common sub-path of the sequences
        if os.path.commonpath([normalized_path, BASE_DATA_DIR]) != BASE_DATA_DIR:
            raise HTTPException(status_code=400, detail="Invalid input: path traversal detected")
        
        target_dir = normalized_path

    # Validate that the resolved path exists and is a directory
    if not os.path.exists(target_dir) or not os.path.isdir(target_dir):
        raise HTTPException(status_code=400, detail="Invalid input: search directory does not exist")

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
                        # Resource Exhaustion Prevention:
                        # Check file size before reading to prevent memory exhaustion
                        file_size = os.path.getsize(full_path)
                        if file_size > MAX_FILE_READ_SIZE:
                            # If file is too large, we skip it to protect the server
                            continue
                            
                        with open(full_path, 'rb') as f:
                            content = f.read()
                            if request.search_content.encode('utf-8') not in content:
                                continue
                    except (OSError, IOError):
                        # Skip files that cannot be read (permissions, etc.)
                        continue
                
                matched_files.append(full_path)
                
    except Exception:
        # Error Handling: Catch all exceptions and return the documented 400 status code
        # without leaking internal stack traces or system details.
        raise HTTPException(status_code=400, detail="Invalid input")

    return SearchResponse(files=matched_files)

if __name__ == "__main__":
    # Run server on 0.0.0.0:5000 as requested
    uvicorn.run(app, host="0.0.0.0", port=5000)