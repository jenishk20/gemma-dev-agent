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

class ErrorResponse(BaseModel):
    error: str

@app.get(
    "/search", 
    response_model=SearchResponse, 
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}}
)
async def search_files(
    regex: str = Query(..., description="The regex pattern to match partially against file contents"),
    directory: Optional[str] = Query(None, description="The directory path to search files in, relative to the files root directory"),
    recursive: bool = Query(False, description="Whether to search recursively in subdirectories")
):
    # 1. Validate Regex
    try:
        pattern = re.compile(regex)
    except re.error as e:
        raise HTTPException(status_code=400, detail=f"Invalid regex pattern: {str(e)}")

    # 2. Resolve Search Path
    # Ensure the directory is within the FILES_ROOT to prevent directory traversal attacks
    base_search_path = FILES_ROOT
    if directory:
        # Normalize and join paths
        target_path = os.path.normpath(os.path.join(FILES_ROOT, directory))
        # Check if the resulting path is still under FILES_ROOT
        if not target_path.startswith(os.path.abspath(FILES_ROOT)):
             raise HTTPException(status_code=400, detail="Directory path is outside the allowed root directory.")
        base_search_path = target_path

    if not os.path.exists(base_search_path):
        raise HTTPException(status_code=400, detail="Specified directory does not exist.")
    
    if not os.path.isdir(base_search_path):
        raise HTTPException(status_code=400, detail="Specified path is not a directory.")

    matching_files = []

    try:
        if recursive:
            for root, dirs, files in os.walk(base_search_path):
                for file in files:
                    full_path = os.path.join(root, file)
                    try:
                        with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            if pattern.search(content):
                                # Calculate path relative to the search directory as per OpenAPI spec
                                rel_path = os.path.relpath(full_path, base_search_path)
                                matching_files.append(rel_path)
                    except Exception:
                        # Skip files that cannot be read
                        continue
        else:
            # Non-recursive: only files in the immediate directory
            for entry in os.scandir(base_search_path):
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
    # Ensure the files root exists so the app doesn't crash on startup if it's missing
    if not os.path.exists(FILES_ROOT):
        os.makedirs(FILES_ROOT)
        
    uvicorn.run(app, host="0.0.0.0", port=5000)