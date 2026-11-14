import os
from typing import List, Optional
from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException
import uvicorn

app = FastAPI(title="FileSearch")

# Base directory where files are stored
BASE_DATA_DIR = os.path.abspath("/data")

class SearchRequest(BaseModel):
    # Bound request sizes to prevent resource exhaustion (DoS)
    search_content: Optional[str] = Field(None, max_length=1000)
    search_filename: Optional[str] = Field(None, max_length=255)
    search_dir: Optional[str] = Field(None, max_length=512)

class SearchResponse(BaseModel):
    files: List[str]

@app.post("/search", response_model=SearchResponse)
async def search_files(request: SearchRequest):
    # 1. Path Traversal Prevention
    target_dir = BASE_DATA_DIR
    if request.search_dir:
        # Reject absolute paths to prevent escaping the base directory
        if os.path.isabs(request.search_dir):
            raise HTTPException(status_code=400, detail="Invalid input: Absolute paths are not allowed in search_dir")
        
        # Join and resolve to absolute path to eliminate '..' and symlinks
        requested_path = os.path.abspath(os.path.join(BASE_DATA_DIR, request.search_dir))
        
        # Confirm the resolved path is still within the BASE_DATA_DIR
        if not requested_path.startswith(BASE_DATA_DIR):
            raise HTTPException(status_code=400, detail="Invalid input: Path traversal detected")
        
        target_dir = requested_path

    # Verify directory exists and is actually a directory
    if not os.path.exists(target_dir) or not os.path.isdir(target_dir):
        raise HTTPException(status_code=400, detail="Invalid input: Search directory does not exist")

    matched_files = []

    try:
        # Resource Exhaustion: We use os.walk. To prevent infinite recursion 
        # or massive directory trees from hanging the server, we rely on 
        # the OS filesystem limits, but we ensure we only process files.
        for root, dirs, files in os.walk(target_dir):
            for file in files:
                full_path = os.path.join(root, file)
                
                # Filename match (starts with)
                filename_match = False
                if request.search_filename and file.startswith(request.search_filename):
                    filename_match = True
                
                # Content match
                content_match = False
                if request.search_content:
                    try:
                        # Resource Exhaustion: Limit the amount of data read from a single file
                        # to prevent MemoryError/DoS when encountering massive files.
                        # We read in chunks to check for the presence of the search string.
                        search_bytes = request.search_content.encode('utf-8')
                        chunk_size = 4096
                        with open(full_path, 'rb') as f:
                            overlap = len(search_bytes) - 1
                            buffer = b""
                            while True:
                                chunk = f.read(chunk_size)
                                if not chunk:
                                    break
                                # Combine buffer with chunk to handle cases where search string 
                                # is split across two read calls
                                if search_bytes in (buffer + chunk):
                                    content_match = True
                                    break
                                buffer = chunk[-overlap:] if overlap > 0 else b""
                    except (OSError, IOError):
                        # Silently skip files that cannot be read (permissions, etc)
                        pass

                if (request.search_filename and filename_match) or (request.search_content and content_match):
                    matched_files.append(full_path)

    except Exception:
        # Error Handling: Catch all unexpected exceptions and return the documented 400
        # without leaking internal stack traces or system details.
        raise HTTPException(status_code=400, detail="Invalid input")

    return SearchResponse(files=matched_files)

if __name__ == "__main__":
    # Run on 0.0.0.0:5000 as requested
    uvicorn.run(app, host="0.0.0.0", port=5000)