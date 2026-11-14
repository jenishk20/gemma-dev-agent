import os
import re
from pathlib import Path
from typing import List, Optional
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
    # 1. Validate Regex
    try:
        pattern = re.compile(regex)
    except re.error as e:
        raise HTTPException(status_code=400, detail=f"Invalid regex pattern: {str(e)}")

    # 2. Resolve and Validate Directory Path (Prevent Directory Traversal)
    # Start from FILES_ROOT
    base_search_path = FILES_ROOT
    if directory:
        # Join and resolve to ensure the path stays within FILES_ROOT
        target_path = (FILES_ROOT / directory).resolve()
        if not str(target_path).startswith(str(FILES_ROOT)):
            raise HTTPException(status_code=400, detail="Directory path is outside the allowed files root.")
        base_search_path = target_path

    if not base_search_path.exists() or not base_search_path.is_dir():
        raise HTTPException(status_code=400, detail="The specified directory does not exist or is not a directory.")

    matching_files = []

    try:
        # 3. Walk through files
        if recursive:
            # Use rglob for recursive search
            for path in base_search_path.rglob("*"):
                if path.is_file():
                    if _file_matches_regex(path, pattern):
                        # Calculate path relative to the search directory as per schema
                        matching_files.append(str(path.relative_to(base_search_path)))
        else:
            # Use glob for non-recursive search
            for path in base_search_path.glob("*"):
                if path.is_file():
                    if _file_matches_regex(path, pattern):
                        matching_files.append(path.name)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

    return SearchResponse(files=matching_files)

def _file_matches_regex(path: Path, pattern: re.Pattern) -> bool:
    """Helper to read file and check for regex match."""
    try:
        # We open in 'r' mode with errors='ignore' to avoid crashing on binary files
        with path.open('r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            if pattern.search(content):
                return True
    except Exception:
        # If file cannot be read, we skip it
        return False
    return False

if __name__ == "__main__":
    # Ensure the files root exists for the demo
    FILES_ROOT.mkdir(parents=True, exist_ok=True)
    uvicorn.run(app, host="0.0.0.0", port=5000)