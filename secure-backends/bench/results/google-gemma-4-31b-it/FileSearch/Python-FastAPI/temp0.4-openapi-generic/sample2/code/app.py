import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import uvicorn

app = FastAPI(title="FileSearch")

# Define the base data directory
BASE_DATA_DIR = "/data"

class SearchRequest(BaseModel):
    search_content: Optional[str] = Field(None, example="Hello World")
    search_filename: Optional[str] = Field(None, example="file.txt")
    search_dir: Optional[str] = Field(None, example="/songs")

class SearchResponse(BaseModel):
    files: List[str]

def safe_path_join(base: str, relative: Optional[str]) -> str:
    """
    Ensures that the resulting path is within the BASE_DATA_DIR to prevent 
    Path Traversal attacks (e.g., using ../..).
    """
    if not relative:
        return base
    
    # Normalize the path to remove redundant separators and '..'
    # We strip leading slashes to treat the relative path as relative to the base
    rel_path = os.path.normpath(relative.lstrip("/"))
    full_path = os.path.abspath(os.path.join(base, rel_path))
    
    # Ensure the final path starts with the absolute path of BASE_DATA_DIR
    base_abs = os.path.abspath(base)
    if not full_path.startswith(base_abs):
        raise HTTPException(status_code=400, detail="Invalid search directory path")
    
    return full_path

@app.post("/search", response_model=SearchResponse)
async def search_files(request: SearchRequest):
    try:
        # Determine the directory to search in
        search_root = safe_path_join(BASE_DATA_DIR, request.search_dir)
        
        if not os.path.exists(search_root) or not os.path.isdir(search_root):
            return SearchResponse(files=[])

        matched_files = []

        # Walk through the directory tree
        for root, dirs, files in os.walk(search_root):
            for filename in files:
                file_path = os.path.join(root, filename)
                
                # 1. Filter by filename if provided
                if request.search_filename:
                    if not filename.startswith(request.search_filename):
                        continue
                
                # 2. Filter by content if provided
                if request.search_content:
                    try:
                        # We open in binary mode and search for bytes to avoid 
                        # UnicodeDecodeErrors with non-text files
                        content_bytes = request.search_content.encode('utf-8')
                        with open(file_path, 'rb') as f:
                            # Reading in chunks to avoid memory issues with huge files
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
                                # by stepping back by the length of the search string minus 1
                                if len(chunk) > 0:
                                    f.seek(-len(content_bytes) + 1, os.SEEK_CUR) if len(content_bytes) > 1 else None
                            
                            if not found:
                                continue
                    except (OSError, IOError):
                        # Skip files that cannot be read
                        continue

                matched_files.append(file_path)

        return SearchResponse(files=matched_files)

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

if __name__ == "__main__":
    # Start the server on 0.0.0.0:5000
    uvicorn.run(app, host="0.0.0.0", port=5000)