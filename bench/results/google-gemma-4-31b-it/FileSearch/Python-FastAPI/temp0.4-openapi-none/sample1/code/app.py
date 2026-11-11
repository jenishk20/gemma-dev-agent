import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

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
    # Determine the root directory to start the search
    # If search_dir is provided, we join it with BASE_DATA_DIR
    # We use os.path.normpath to prevent directory traversal attacks (e.g., ../../)
    root_path = BASE_DATA_DIR
    if request.search_dir:
        # Ensure the search_dir is treated as relative to BASE_DATA_DIR
        # Remove leading slash to ensure os.path.join works correctly
        rel_dir = request.search_dir.lstrip('/')
        root_path = os.path.join(BASE_DATA_DIR, rel_dir)
    
    # Security check: Ensure the resolved path is actually inside /data
    if not os.path.normpath(root_path).startswith(os.path.normpath(BASE_DATA_DIR)):
        raise HTTPException(status_code=400, detail="Invalid search directory")

    if not os.path.exists(root_path):
        # If the directory doesn't exist, we return an empty list as per standard search behavior
        return SearchResponse(files=[])

    matched_files = []

    try:
        for root, dirs, files in os.walk(root_path):
            for file in files:
                full_path = os.path.join(root, file)
                
                # 1. Check filename match (starts with)
                if request.search_filename:
                    if file.startswith(request.search_filename):
                        matched_files.append(full_path)
                        continue # Move to next file if filename matched
                
                # 2. Check content match
                if request.search_content:
                    try:
                        # We open in binary mode and search for bytes to avoid encoding crashes
                        # with non-text files
                        with open(full_path, 'rb') as f:
                            content = f.read()
                            if request.search_content.encode('utf-8') in content:
                                matched_files.append(full_path)
                    except (OSError, IOError):
                        # Skip files that cannot be read
                        continue
                
                # If both are None, the logic implies we aren't searching for anything specific,
                # but the schema suggests we search if content OR filename is provided.
                # If neither is provided, we don't add the file.

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"An error occurred during search: {str(e)}")

    # Remove duplicates in case a file matched both filename and content
    return SearchResponse(files=list(set(matched_files)))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)