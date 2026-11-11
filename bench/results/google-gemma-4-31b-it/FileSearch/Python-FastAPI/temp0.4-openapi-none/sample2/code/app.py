import os
from typing import List, Optional
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException
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
    # If search_dir is provided, it is treated as relative to /data
    target_dir = BASE_DATA_DIR
    if request.search_dir:
        # Normalize path to prevent directory traversal attacks
        # Ensure the resulting path is still within /data
        requested_path = os.path.normpath(os.path.join(BASE_DATA_DIR, request.search_dir))
        if not requested_path.startswith(BASE_DATA_DIR):
            raise HTTPException(status_code=400, detail="Invalid search_dir: Path must be within /data")
        target_dir = requested_path

    if not os.path.exists(target_dir) or not os.path.isdir(target_dir):
        # If the directory doesn't exist, we return an empty list or 400 depending on interpretation
        # Given the schema, returning an empty list of files is safer, but 400 is specified for invalid input.
        raise HTTPException(status_code=400, detail="Invalid search directory")

    matched_files = []

    try:
        for root, dirs, files in os.walk(target_dir):
            for file in files:
                full_path = os.path.join(root, file)
                
                # 1. Check filename match (starts with)
                filename_match = False
                if request.search_filename and file.startswith(request.search_filename):
                    filename_match = True
                
                # 2. Check content match
                content_match = False
                if request.search_content:
                    try:
                        # We open in binary mode and search for bytes to avoid decoding errors on non-text files
                        with open(full_path, 'rb') as f:
                            content = f.read()
                            if request.search_content.encode('utf-8') in content:
                                content_match = True
                    except (OSError, IOError):
                        # Skip files that cannot be read
                        pass

                # Logic: If both are provided, we usually treat it as an OR or AND. 
                # The prompt says "contain the specified content OR match the filename".
                if (request.search_filename and filename_match) or (request.search_content and content_match):
                    matched_files.append(full_path)
                elif not request.search_filename and not request.search_content:
                    # If neither is provided, the behavior isn't explicitly defined, 
                    # but typically we return nothing or everything. We'll return nothing.
                    pass

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    return SearchResponse(files=matched_files)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)