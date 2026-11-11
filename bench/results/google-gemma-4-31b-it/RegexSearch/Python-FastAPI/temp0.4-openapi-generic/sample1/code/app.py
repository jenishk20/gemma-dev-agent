import os
import re
from typing import List, Optional
from fastapi import FastAPI, Query, HTTPException
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

    # 2. Resolve and Validate Directory Path (Prevent Directory Traversal)
    # Default to root of ./files if no directory is provided
    search_sub_dir = directory if directory else ""
    
    # Join root with user input and resolve absolute path
    target_path = os.path.abspath(os.path.join(FILES_ROOT, search_sub_dir))

    # Security Check: Ensure the resolved path is actually inside FILES_ROOT
    if not target_path.startswith(FILES_ROOT):
        raise HTTPException(status_code=400, detail="Invalid directory: Path must be within the files root directory.")

    if not os.path.exists(target_path) or not os.path.isdir(target_path):
        raise HTTPException(status_code=400, detail="The specified directory does not exist or is not a directory.")

    matching_files = []

    try:
        # 3. Walk through files
        if recursive:
            for root, dirs, files in os.walk(target_path):
                for file in files:
                    full_path = os.path.join(root, file)
                    if _check_file_content(full_path, pattern):
                        # Calculate path relative to the search directory as per schema
                        rel_path = os.path.relpath(full_path, target_path)
                        matching_files.append(rel_path)
        else:
            # Non-recursive: only list files in the immediate target_path
            try:
                for entry in os.scandir(target_path):
                    if entry.is_file():
                        if _check_file_content(entry.path, pattern):
                            matching_files.append(entry.name)
            except PermissionError:
                raise HTTPException(status_code=400, detail="Permission denied accessing directory.")

    except Exception as e:
        # Generic catch for unexpected OS errors
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

    return SearchResponse(files=matching_files)

def _check_file_content(file_path: str, pattern: re.Pattern) -> bool:
    """Helper to check if a file's content matches the regex."""
    try:
        # We open in 'rb' and decode to handle potential encoding issues gracefully
        # or use 'r' with errors='ignore' to ensure the app doesn't crash on binary files
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            if pattern.search(content):
                return True
    except Exception:
        # If a file cannot be read, we skip it
        return False
    return False

if __name__ == "__main__":
    # Ensure the files root exists so the app doesn't fail on startup if the folder is missing
    if not os.path.exists(FILES_ROOT):
        os.makedirs(FILES_ROOT)
        
    uvicorn.run(app, host="0.0.0.0", port=5000)