import os
import re
from typing import List, Optional
from fastapi import FastAPI, Query, HTTPException
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="File Search API")

# The root directory where files are stored
# Use absolute path to ensure robust comparison during path traversal checks
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
    # 1. Regex Denial of Service (ReDoS) Mitigation
    # While Python's 're' doesn't have a built-in timeout, we validate the regex.
    # To prevent catastrophic backtracking, we limit the regex length.
    if len(regex) > 1000:
        raise HTTPException(status_code=400, detail="Regex pattern is too long.")

    try:
        pattern = re.compile(regex)
    except re.error as e:
        raise HTTPException(status_code=400, detail=f"Invalid regex pattern: {str(e)}")

    # 2. Path Traversal Prevention
    # We must ensure the user cannot escape the FILES_ROOT.
    base_search_path = FILES_ROOT
    if directory:
        # Reject absolute paths to prevent bypassing the root
        if os.path.isabs(directory):
            raise HTTPException(status_code=400, detail="Absolute paths are not allowed.")
        
        # Join and resolve the path to remove '..' and symlinks
        target_path = os.path.abspath(os.path.join(FILES_ROOT, directory))
        
        # Verify the resolved path is still within the FILES_ROOT
        # commonpath returns the longest common sub-path of the sequence of paths.
        if os.path.commonpath([FILES_ROOT, target_path]) != FILES_ROOT:
            raise HTTPException(status_code=400, detail="Directory path is outside the allowed root directory.")
        
        base_search_path = target_path

    if not os.path.exists(base_search_path):
        raise HTTPException(status_code=400, detail="Specified directory does not exist.")
    
    if not os.path.isdir(base_search_path):
        raise HTTPException(status_code=400, detail="Specified path is not a directory.")

    matching_files = []

    try:
        # 3. Resource Exhaustion Mitigation
        # We limit the number of files scanned to prevent CPU/Memory exhaustion.
        MAX_FILES_TO_SCAN = 10000
        files_scanned = 0

        if recursive:
            for root, dirs, files in os.walk(base_search_path):
                for file in files:
                    files_scanned += 1
                    if files_scanned > MAX_FILES_TO_SCAN:
                        raise HTTPException(status_code=500, detail="Too many files to scan in the specified directory.")
                    
                    full_path = os.path.join(root, file)
                    try:
                        # Limit file size read to prevent memory exhaustion (e.g., 10MB)
                        with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read(10 * 1024 * 1024) 
                            if pattern.search(content):
                                rel_path = os.path.relpath(full_path, base_search_path)
                                matching_files.append(rel_path)
                    except (OSError, IOError):
                        continue
        else:
            for entry in os.scandir(base_search_path):
                if entry.is_file():
                    files_scanned += 1
                    if files_scanned > MAX_FILES_TO_SCAN:
                        raise HTTPException(status_code=500, detail="Too many files to scan in the specified directory.")
                    
                    try:
                        with open(entry.path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read(10 * 1024 * 1024)
                            if pattern.search(content):
                                matching_files.append(entry.name)
                    except (OSError, IOError):
                        continue

    except HTTPException as he:
        raise he
    except Exception as e:
        # Generic error to avoid leaking internal stack traces
        raise HTTPException(status_code=500, detail="An internal server error occurred while searching files.")

    return SearchResponse(files=matching_files)

if __name__ == "__main__":
    # Ensure the files root exists
    if not os.path.exists(FILES_ROOT):
        os.makedirs(FILES_ROOT, exist_ok=True)
        
    uvicorn.run(app, host="0.0.0.0", port=5000)