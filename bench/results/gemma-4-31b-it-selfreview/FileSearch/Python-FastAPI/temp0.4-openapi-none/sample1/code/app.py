import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="FileSearch")

# Base directory where files are stored
BASE_DATA_DIR = os.path.normpath("/data")

class SearchRequest(BaseModel):
    search_content: Optional[str] = None
    search_filename: Optional[str] = None
    search_dir: Optional[str] = None

class SearchResponse(BaseModel):
    files: List[str]

@app.post("/search", response_model=SearchResponse)
async def search_files(request: SearchRequest):
    # 1. Path Traversal Prevention
    # Start with the base directory
    root_path = BASE_DATA_DIR
    
    if request.search_dir:
        # Reject absolute paths to prevent escaping the root via /etc/passwd etc.
        if os.path.isabs(request.search_dir):
            raise HTTPException(status_code=400, detail="Invalid input: absolute paths are not allowed in search_dir")
        
        # Join and normalize the path to resolve '..' and '.'
        # os.path.join handles relative paths, but we must normalize to check the final location
        requested_path = os.path.normpath(os.path.join(BASE_DATA_DIR, request.search_dir))
        
        # Confirm the resolved path still resides within BASE_DATA_DIR
        if not requested_path.startswith(BASE_DATA_DIR + os.sep) and requested_path != BASE_DATA_DIR:
            raise HTTPException(status_code=400, detail="Invalid input: path traversal detected")
        
        root_path = requested_path

    # Check if the directory exists and is actually a directory
    if not os.path.isdir(root_path):
        # Return empty list if directory doesn't exist or is a file, as per search behavior
        return SearchResponse(files=[])

    matched_files = []

    try:
        # Resource Exhaustion: Use a generator (os.walk) to avoid loading all file names into memory at once
        for root, dirs, files in os.walk(root_path):
            for file in files:
                full_path = os.path.join(root, file)
                
                # 2. Filename matching
                if request.search_filename:
                    if file.startswith(request.search_filename):
                        matched_files.append(full_path)
                        # If it matches filename, we don't need to check content for this file
                        continue 
                
                # 3. Content matching
                if request.search_content:
                    try:
                        # Resource Exhaustion: Read file in chunks to prevent memory exhaustion 
                        # from extremely large files.
                        search_bytes = request.search_content.encode('utf-8')
                        chunk_size = 4096
                        with open(full_path, 'rb') as f:
                            overlap = len(search_bytes) - 1
                            buffer = b""
                            while True:
                                chunk = f.read(chunk_size)
                                if not chunk:
                                    break
                                # Combine overlap from previous chunk to catch patterns split across chunks
                                if search_bytes in (buffer + chunk):
                                    matched_files.append(full_path)
                                    break
                                buffer = chunk[-overlap:] if overlap > 0 else b""
                    except (OSError, IOError):
                        # Skip files that cannot be read (permissions, etc.)
                        continue
                
    except Exception:
        # Error Handling: Catch all to prevent leaking stack traces, return 400 as per schema
        raise HTTPException(status_code=400, detail="Invalid input")

    # Remove duplicates and return
    return SearchResponse(files=list(set(matched_files)))

if __name__ == "__main__":
    import uvicorn
    # Run on 0.0.0.0:5000 as requested
    uvicorn.run(app, host="0.0.0.0", port=5000)