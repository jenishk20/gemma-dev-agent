import os
import re
from typing import List, Optional
from fastapi import FastAPI, Query, HTTPException
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="File Search API")

# The root directory where files are stored
FILES_ROOT = os.path.abspath("./files")

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
    # 1. Validate and compile Regex
    try:
        pattern = re.compile(regex)
    except re.error as e:
        raise HTTPException(status_code=400, detail=f"Invalid regex pattern: {str(e)}")

    # 2. Resolve and validate the search directory
    # Prevent Directory Traversal attacks by ensuring the path stays within FILES_ROOT
    search_path = directory if directory else ""
    # Remove leading slashes to treat it as relative
    search_path = search_path.lstrip("/")
    full_search_path = os.path.abspath(os.path.join(FILES_ROOT, search_path))

    if not full_search_path.startswith(FILES_ROOT):
        raise HTTPException(status_code=400, detail="Invalid directory: Path must be within the files root directory.")

    if not os.path.exists(full_search_path) or not os.path.isdir(full_search_path):
        raise HTTPException(status_code=400, detail="The specified directory does not exist or is not a directory.")

    matching_files = []

    try:
        # 3. Walk through files
        if recursive:
            for root, dirs, files in os.walk(full_search_path):
                for filename in files:
                    file_path = os.path.join(root, filename)
                    if _check_file_content(file_path, pattern):
                        # Calculate path relative to the requested search directory
                        rel_path = os.path.relpath(file_path, full_search_path)
                        matching_files.append(rel_path)
        else:
            # Non-recursive: only look at files in the immediate directory
            for entry in os.scandir(full_search_path):
                if entry.is_file():
                    if _check_file_content(entry.path, pattern):
                        matching_files.append(entry.name)

    except Exception as e:
        # Log the error internally and return a 500
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

    return SearchResponse(files=matching_files)

def _check_file_content(path: str, pattern: re.Pattern) -> bool:
    """Helper to read file and check for regex match."""
    try:
        # We open in binary mode and decode to avoid encoding crashes, 
        # or use errors='ignore' to handle non-text files gracefully.
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            if pattern.search(content):
                return True
    except Exception:
        # If a file cannot be read, we skip it
        pass
    return False

if __name__ == "__main__":
    # Ensure the files root exists so the app doesn't crash on start
    if not os.path.exists(FILES_ROOT):
        os.makedirs(FILES_ROOT)
        
    uvicorn.run(app, host="0.0.0.0", port=5000)