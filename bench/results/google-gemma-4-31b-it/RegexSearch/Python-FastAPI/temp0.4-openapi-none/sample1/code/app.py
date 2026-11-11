import os
import re
from typing import List, Optional
from fastapi import FastAPI, Query, HTTPException
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="File Search API")

# The root directory where files are stored
FILES_ROOT = "./files"

class SearchResponse(BaseModel):
    files: List[str]

@app.get("/search", response_model=SearchResponse)
async def search_files(
    regex: str = Query(..., description="The regex pattern to match partially against file contents"),
    directory: Optional[str] = Query(None, description="The directory path to search files in, relative to the files root directory"),
    recursive: bool = Query(False, description="Whether to search recursively in subdirectories")
):
    # Validate regex
    try:
        pattern = re.compile(regex)
    except re.error as e:
        raise HTTPException(status_code=400, detail=f"Invalid regex pattern: {str(e)}")

    # Determine the base search path
    search_base = FILES_ROOT
    if directory:
        # Prevent directory traversal attacks by ensuring the path stays within FILES_ROOT
        normalized_dir = os.path.normpath(directory).lstrip(os.sep).lstrip('/')
        search_base = os.path.join(FILES_ROOT, normalized_dir)
        
        if not os.path.exists(search_base) or not os.path.isdir(search_base):
            raise HTTPException(status_code=400, detail="Specified directory does not exist or is not a directory")

    matching_files = []

    try:
        if recursive:
            for root, dirs, files in os.walk(search_base):
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            if pattern.search(content):
                                # Calculate path relative to the search_base or FILES_ROOT as per schema
                                # Schema says "relative to the indicated directory" (which is directory param)
                                # If directory is provided, we return relative to that.
                                rel_path = os.path.relpath(file_path, search_base if directory else FILES_ROOT)
                                matching_files.append(rel_path)
                    except Exception:
                        continue # Skip files that cannot be read
        else:
            if not os.path.exists(search_base):
                raise HTTPException(status_code=400, detail="Directory not found")
            
            for entry in os.scandir(search_base):
                if entry.is_file():
                    try:
                        with open(entry.path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            if pattern.search(content):
                                matching_files.append(entry.name)
                    except Exception:
                        continue

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

    return SearchResponse(files=matching_files)

if __name__ == "__main__":
    # Ensure the files root exists so the app doesn't crash on startup if missing
    if not os.path.exists(FILES_ROOT):
        os.makedirs(FILES_ROOT)
        
    uvicorn.run(app, host="0.0.0.0", port=5000)