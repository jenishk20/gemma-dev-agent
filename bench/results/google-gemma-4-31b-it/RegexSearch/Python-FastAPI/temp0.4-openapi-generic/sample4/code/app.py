import os
import re
from typing import List, Optional
from pathlib import Path
from fastapi import FastAPI, Query, HTTPException
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="File Search API")

# Define the root directory for files
FILES_ROOT = Path("./files").resolve()

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
    regex: str = Query(..., description="The regex pattern to match against file contents"),
    directory: Optional[str] = Query(None, description="The directory path relative to the files root"),
    recursive: bool = Query(False, description="Whether to search recursively in subdirectories")
):
    # 1. Validate and resolve the search directory to prevent Directory Traversal
    try:
        # If directory is not provided, use the root
        search_base = FILES_ROOT if not directory else (FILES_ROOT / directory).resolve()
        
        # Security Check: Ensure the resolved path is still within the FILES_ROOT
        if not str(search_base).startswith(str(FILES_ROOT)):
            raise HTTPException(status_code=400, detail="Invalid directory: Path is outside the allowed root directory.")
        
        if not search_base.exists() or not search_base.is_dir():
            raise HTTPException(status_code=400, detail="The specified directory does not exist or is not a directory.")
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=400, detail=f"Invalid directory path: {str(e)}")

    # 2. Compile the regex pattern
    try:
        pattern = re.compile(regex)
    except re.error:
        raise HTTPException(status_code=400, detail="Invalid regular expression pattern.")

    matching_files = []

    try:
        # 3. Iterate through files
        # We use os.walk or rglob based on the recursive flag
        if recursive:
            # rglob('*') finds all files recursively
            for path in search_base.rglob('*'):
                if path.is_file():
                    if _check_file_content(path, pattern):
                        # Calculate path relative to the search_base as per OpenAPI spec
                        matching_files.append(str(path.relative_to(search_base)))
        else:
            # iterdir() only looks at the current level
            for path in search_base.iterdir():
                if path.is_file():
                    if _check_file_content(path, pattern):
                        matching_files.append(path.name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error during file search: {str(e)}")

    return SearchResponse(files=matching_files)

def _check_file_content(file_path: Path, pattern: re.Pattern) -> bool:
    """
    Helper to read file content and check for regex match.
    Handles binary files by attempting to read as text and ignoring decoding errors.
    """
    try:
        # We read the file in chunks or as a whole. For a general search API, 
        # reading the content as text is standard.
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            if pattern.search(content):
                return True
    except Exception:
        # If the file cannot be read, we skip it
        return False
    return False

if __name__ == "__main__":
    # Ensure the files root exists so the app doesn't crash on startup
    FILES_ROOT.mkdir(parents=True, exist_ok=True)
    
    # Start the server on 0.0.0.0:5000
    uvicorn.run(app, host="0.0.0.0", port=5000)