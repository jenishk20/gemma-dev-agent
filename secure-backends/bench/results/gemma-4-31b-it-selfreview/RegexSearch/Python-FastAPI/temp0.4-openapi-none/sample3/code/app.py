import os
import re
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="File Search API")

# Define the root directory for files
FILES_ROOT = os.path.abspath("./files")

class SearchResponse(BaseModel):
    files: List[str]

class ErrorResponse(BaseModel):
    error: str

@app.get(
    "/search",
    summary="Search files by regex",
    description="Searches files in a specified directory and returns files whose content matches the given regex.",
    responses={
        200: {"model": SearchResponse},
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    }
)
async def search_files(
    regex: str = Query(..., description="The regex pattern to match partially against file contents"),
    directory: Optional[str] = Query(None, description="The directory path to search files in, relative to the files root directory"),
    recursive: bool = Query(False, description="Whether to search recursively in subdirectories")
):
    # 1. Regex Denial of Service (ReDoS) mitigation
    # While Python's 're' doesn't have a built-in timeout, we can limit the length of the regex 
    # to prevent extremely complex patterns from being compiled/executed.
    if len(regex) > 1000:
        raise HTTPException(status_code=400, detail="Regex pattern is too long.")

    try:
        pattern = re.compile(regex)
    except re.error as e:
        raise HTTPException(status_code=400, detail=f"Invalid regex pattern: {str(e)}")

    # 2. Path Traversal Mitigation
    # We must ensure the user cannot escape the FILES_ROOT.
    # We reject absolute paths and '..' components explicitly.
    if directory:
        if os.path.isabs(directory) or ".." in directory:
            raise HTTPException(status_code=400, detail="Invalid directory path: absolute paths and '..' are not allowed.")
        
        # Join and resolve to absolute path to verify it is still within FILES_ROOT
        search_base = os.path.abspath(os.path.join(FILES_ROOT, directory))
    else:
        search_base = FILES_ROOT

    # Final check: ensure the resolved path starts with the root directory
    if not search_base.startswith(FILES_ROOT):
        raise HTTPException(status_code=400, detail="Directory path is outside the allowed files root.")

    if not os.path.exists(search_base):
        raise HTTPException(status_code=400, detail="Specified directory does not exist.")
    
    if not os.path.isdir(search_base):
        raise HTTPException(status_code=400, detail="Specified path is not a directory.")

    matching_files = []

    try:
        if recursive:
            for root, dirs, files in os.walk(search_base):
                for file in files:
                    full_path = os.path.join(root, file)
                    if _check_file_content(full_path, pattern):
                        rel_path = os.path.relpath(full_path, search_base)
                        matching_files.append(rel_path)
        else:
            for entry in os.scandir(search_base):
                if entry.is_file():
                    if _check_file_content(entry.path, pattern):
                        matching_files.append(entry.name)
    except Exception as e:
        # Generic error to avoid leaking internal system details
        raise HTTPException(status_code=500, detail="An internal server error occurred during file search.")

    return SearchResponse(files=matching_files)

def _check_file_content(file_path: str, pattern: re.Pattern) -> bool:
    """Helper to check if a file's content matches the regex with resource limits."""
    try:
        # Resource Exhaustion Mitigation: Limit the amount of data read from a file
        # to prevent memory exhaustion (e.g., reading a multi-gigabyte log file).
        MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB limit per file
        
        file_size = os.path.getsize(file_path)
        if file_size > MAX_FILE_SIZE:
            # We treat files too large as no-match or we could log a warning.
            # To keep API behavior consistent, we skip them.
            return False

        with open(file_path, 'rb') as f:
            content = f.read().decode('utf-8', errors='ignore')
            return bool(pattern.search(content))
    except (OSError, IOError):
        # Handle inaccessible files (permissions, etc.)
        return False
    except Exception:
        return False

if __name__ == "__main__":
    # Ensure the files root exists
    if not os.path.exists(FILES_ROOT):
        os.makedirs(FILES_ROOT, exist_ok=True)
        
    uvicorn.run(app, host="0.0.0.0", port=5000)