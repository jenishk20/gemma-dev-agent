import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import uvicorn

app = FastAPI(title="FileSearch")

# The base directory where files are stored
BASE_DATA_DIR = "/data"

class SearchRequest(BaseModel):
    search_content: Optional[str] = Field(default=None, example="Hello World")
    search_filename: Optional[str] = Field(default=None, example="file.txt")
    search_dir: Optional[str] = Field(default=None, example="/songs")

class SearchResponse(BaseModel):
    files: List[str]

def safe_path_resolve(relative_path: Optional[str]) -> str:
    """
    Ensures that the resolved path stays within the /data directory 
    to prevent Directory Traversal attacks.
    """
    if not relative_path:
        return BASE_DATA_DIR
    
    # Normalize path and remove leading slash to treat it as relative to BASE_DATA_DIR
    clean_rel = relative_path.lstrip("/")
    full_path = os.path.abspath(os.path.join(BASE_DATA_DIR, clean_rel))
    
    if not full_path.startswith(os.path.abspath(BASE_DATA_DIR)):
        raise HTTPException(status_code=400, detail="Invalid search directory: Path is outside of data directory")
    
    return full_path

@app.post("/search", response_model=SearchResponse)
async def search_files(request: SearchRequest):
    try:
        root_search_path = safe_path_resolve(request.search_dir)
    except HTTPException as e:
        raise e

    if not os.path.exists(root_search_path) or not os.path.isdir(root_search_path):
        # If the directory doesn't exist, we return an empty list rather than 400 
        # to maintain API stability, or 400 if the input was logically invalid.
        return SearchResponse(files=[])

    matched_files = []

    # Walk through the directory tree
    for root, dirs, files in os.walk(root_search_path):
        for filename in files:
            full_path = os.path.join(root, filename)
            
            # 1. Check filename match (starts with or equals)
            name_match = False
            if request.search_filename and filename.startswith(request.search_filename):
                name_match = True
            
            # 2. Check content match
            content_match = False
            if request.search_content:
                try:
                    # We open in binary mode and decode to handle potential encoding issues 
                    # and avoid crashing on non-text files.
                    with open(full_path, 'rb') as f:
                        # Read in chunks to avoid memory overflow with huge files
                        while True:
                            chunk = f.read(8192)
                            if not chunk:
                                break
                            if request.search_content.encode('utf-8') in chunk:
                                content_match = True
                                break
                except (OSError, IOError):
                    # Skip files that cannot be read (permissions, etc.)
                    content_match = False

            # If either condition is met (or if both are null, we don't match everything by default)
            # The logic: if both are null, return nothing. If either is provided, check match.
            if (request.search_filename or request.search_content):
                if name_match or content_match:
                    matched_files.append(full_path)

    return SearchResponse(files=matched_files)

if __name__ == "__main__":
    # Run the server on 0.0.0.0:5000
    uvicorn.run(app, host="0.0.0.0", port=5000)