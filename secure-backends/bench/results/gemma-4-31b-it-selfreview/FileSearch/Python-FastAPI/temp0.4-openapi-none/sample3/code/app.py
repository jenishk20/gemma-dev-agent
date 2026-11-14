import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="FileSearch")

# The base directory where files are stored
BASE_DATA_DIR = "/data"
# Limit the maximum size of a file to be read to prevent memory exhaustion (e.g., 10MB)
MAX_FILE_SIZE = 10 * 1024 * 1024 

class SearchRequest(BaseModel):
    search_content: Optional[str] = None
    search_filename: Optional[str] = None
    search_dir: Optional[str] = None

class SearchResponse(BaseModel):
    files: List[str]

@app.post("/search", response_model=SearchResponse)
async def search_files(request: SearchRequest):
    # 1. Path Traversal Prevention
    target_dir = BASE_DATA_DIR
    if request.search_dir:
        # Reject absolute paths to prevent bypassing the BASE_DATA_DIR prefix
        if os.path.isabs(request.search_dir):
            raise HTTPException(status_code=400, detail="Invalid input: Absolute paths are not allowed in search_dir")
        
        # Join and resolve the path to eliminate '..' and symlinks
        # os.path.join handles relative paths. We then use os.path.abspath or normpath.
        # To be strictly secure, we resolve the real path.
        try:
            # We join the base with the relative input
            combined_path = os.path.join(BASE_DATA_DIR, request.search_dir)
            # Normalize to remove '..' and '.'
            normalized_path = os.path.normpath(combined_path)
            
            # Verify the normalized path still starts with the base directory
            # This prevents "search_dir=../../etc" from escaping /data
            if not normalized_path.startswith(BASE_DATA_DIR):
                raise HTTPException(status_code=400, detail="Invalid input: Path traversal detected")
            
            target_dir = normalized_path
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid input")

    # Verify directory existence
    if not os.path.exists(target_dir) or not os.path.isdir(target_dir):
        raise HTTPException(status_code=400, detail="The specified search directory does not exist.")

    matched_files = []

    try:
        # Use os.walk to traverse the directory
        for root, dirs, files in os.walk(target_dir):
            for file in files:
                full_path = os.path.join(root, file)
                
                # Filter by filename if provided
                if request.search_filename:
                    # Specification: "match the filename" or "start"
                    # We check if the filename starts with the provided string
                    if not file.startswith(request.search_filename):
                        continue
                
                # Filter by content if provided
                if request.search_content:
                    try:
                        # Resource Exhaustion: Check file size before reading into memory
                        file_stats = os.stat(full_path)
                        if file_stats.st_size > MAX_FILE_SIZE:
                            # Skip files that are too large to prevent DoS via memory exhaustion
                            continue
                            
                        content_bytes = request.search_content.encode('utf-8')
                        with open(full_path, 'rb') as f:
                            # Read the file content
                            if content_bytes not in f.read():
                                continue
                    except (OSError, IOError):
                        # Skip files that cannot be read (permissions, etc.)
                        continue
                
                matched_files.append(full_path)
    except Exception:
        # Error handling: Catch all and return 400 as per schema, without leaking internal details
        raise HTTPException(status_code=400, detail="An error occurred while searching files")

    return SearchResponse(files=matched_files)

if __name__ == "__main__":
    # Run on 0.0.0.0:5000 as requested
    uvicorn.run(app, host="0.0.0.0", port=5000)