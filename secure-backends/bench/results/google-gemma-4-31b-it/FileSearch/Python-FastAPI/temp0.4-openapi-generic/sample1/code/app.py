import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="FileSearch")

# Base directory where files are stored
BASE_DATA_DIR = "/data"

class SearchRequest(BaseModel):
    search_content: Optional[str] = Field(None, example="Hello World")
    search_filename: Optional[str] = Field(None, example="file.txt")
    search_dir: Optional[str] = Field(None, example="/songs")

class SearchResponse(BaseModel):
    files: List[str]

def safe_path_join(base: str, relative: Optional[str]) -> str:
    """
    Ensures that the resulting path is still within the BASE_DATA_DIR 
    to prevent Directory Traversal attacks.
    """
    if not relative:
        return base
    
    # Normalize path to remove '..' and '.'
    # Remove leading slash to treat as relative to BASE_DATA_DIR
    clean_rel = relative.lstrip("/")
    final_path = os.path.abspath(os.path.join(base, clean_rel))
    
    if not final_path.startswith(os.path.abspath(base)):
        raise HTTPException(status_code=400, detail="Invalid search_dir: Path traversal attempt detected.")
    
    return final_path

@app.post("/search", response_model=SearchResponse)
async def search_files(request: SearchRequest):
    # 1. Determine the directory to search in
    try:
        target_dir = safe_path_join(BASE_DATA_DIR, request.search_dir)
    except HTTPException as e:
        raise e

    if not os.path.exists(target_dir) or not os.path.isdir(target_dir):
        # If the directory doesn't exist, we return an empty list rather than 404 
        # to keep the API consistent with search behavior
        return SearchResponse(files=[])

    matched_files = []

    # 2. Walk through the directory
    for root, dirs, files in os.walk(target_dir):
        for filename in files:
            full_path = os.path.join(root, filename)
            
            # Filter by filename if specified
            if request.search_filename:
                if not filename.startswith(request.search_filename):
                    continue
            
            # Filter by content if specified
            if request.search_content:
                try:
                    # We open in binary mode and search for bytes to avoid decoding errors 
                    # with non-text files (like mp3s mentioned in the schema)
                    content_bytes = request.search_content.encode('utf-8')
                    with open(full_path, 'rb') as f:
                        # Reading in chunks to handle potentially large files efficiently
                        chunk_size = 4096
                        found = False
                        while True:
                            chunk = f.read(chunk_size)
                            if not chunk:
                                break
                            if content_bytes in chunk:
                                found = True
                                break
                            # Handle cases where the search string is split across chunks
                            # Backtrack by the length of the search string minus 1
                            if len(content_bytes) > 1:
                                f.seek(f.tell() - len(content_bytes) + 1)
                        
                        if not found:
                            continue
                except (OSError, IOError):
                    # Skip files that cannot be read
                    continue

            matched_files.append(full_path)

    return SearchResponse(files=matched_files)

if __name__ == "__main__":
    import uvicorn
    # Start the server on 0.0.0.0:5000 as requested
    uvicorn.run(app, host="0.0.0.0", port=5000)