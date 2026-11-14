import os
import re
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="File Search API")

# Define the root directory for files
FILES_ROOT = "./files"

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
    # Validate regex
    try:
        pattern = re.compile(regex)
    except re.error as e:
        raise HTTPException(status_code=400, detail=f"Invalid regex pattern: {str(e)}")

    # Determine the base search path
    # If directory is provided, join it with FILES_ROOT. If not, use FILES_ROOT.
    search_base = os.path.join(FILES_ROOT, directory if directory else "")
    
    # Security check: Ensure the search_base is actually within FILES_ROOT to prevent directory traversal
    abs_root = os.path.abspath(FILES_ROOT)
    abs_search_path = os.path.abspath(search_base)
    if not abs_search_path.startswith(abs_root):
        raise HTTPException(status_code=400, detail="Directory path is outside the allowed files root.")

    if not os.path.exists(abs_search_path):
        raise HTTPException(status_code=400, detail="Specified directory does not exist.")
    
    if not os.path.isdir(abs_search_path):
        raise HTTPException(status_code=400, detail="Specified path is not a directory.")

    matching_files = []

    try:
        if recursive:
            for root, dirs, files in os.walk(abs_search_path):
                for file in files:
                    full_path = os.path.join(root, file)
                    if _check_file_content(full_path, pattern):
                        # Calculate relative path from the search_base
                        rel_path = os.path.relpath(full_path, abs_search_path)
                        # If a directory was specified, the API expects paths relative to that directory
                        # but the schema says "relative to the indicated directory".
                        # We provide the path relative to the search_base.
                        matching_files.append(rel_path)
        else:
            # Non-recursive: only files directly in the search_base
            for entry in os.scandir(abs_search_path):
                if entry.is_file():
                    if _check_file_content(entry.path, pattern):
                        matching_files.append(entry.name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

    return SearchResponse(files=matching_files)

def _check_file_content(file_path: str, pattern: re.Pattern) -> bool:
    """Helper to check if a file's content matches the regex."""
    try:
        # We open in binary mode and decode with 'utf-8' ignoring errors to handle 
        # potential binary files or different encodings without crashing.
        with open(file_path, 'rb') as f:
            content = f.read().decode('utf-8', errors='ignore')
            return bool(pattern.search(content))
    except Exception:
        # If file cannot be read, we treat it as no match
        return False

if __name__ == "__main__":
    # Ensure the files root exists so the app doesn't crash on first request if folder is missing
    if not os.path.exists(FILES_ROOT):
        os.makedirs(FILES_ROOT)
        
    uvicorn.run(app, host="0.0.0.0", port=5000)