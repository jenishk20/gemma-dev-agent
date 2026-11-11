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
    # 1. Regex Denial of Service (ReDoS) mitigation
    # While Python's 're' doesn't have a built-in timeout, we can limit the length of the regex
    # to prevent extremely complex patterns from being compiled/executed.
    if len(regex) > 1000:
        raise HTTPException(status_code=400, detail="Regex pattern is too long.")

    try:
        pattern = re.compile(regex)
    except re.error as e:
        raise HTTPException(status_code=400, detail=f"Invalid regex pattern: {str(e)}")

    # 2. Path Traversal Prevention
    # Reject absolute paths and '..' to prevent escaping the root directory
    search_base = directory if directory else ""
    if search_base:
        if os.path.isabs(search_base) or ".." in search_base:
            raise HTTPException(status_code=400, detail="Invalid directory path: absolute paths and '..' are not allowed.")

    # Resolve the final path and verify it is still within FILES_ROOT
    full_search_path = os.path.abspath(os.path.join(FILES_ROOT, search_base))
    if not full_search_path.startswith(FILES_ROOT):
        raise HTTPException(status_code=400, detail="Directory path is outside the allowed files root.")

    if not os.path.exists(full_search_path):
        raise HTTPException(status_code=400, detail="Specified directory does not exist.")
    
    if not os.path.isdir(full_search_path):
        raise HTTPException(status_code=400, detail="Specified path is not a directory.")

    matching_files = []

    try:
        # 3. Resource Exhaustion Mitigation
        # Limit the number of files processed to prevent server hang/memory exhaustion
        MAX_FILES_TO_SCAN = 10000 
        files_scanned = 0

        if recursive:
            for root, dirs, files in os.walk(full_search_path):
                for file in files:
                    files_scanned += 1
                    if files_scanned > MAX_FILES_TO_SCAN:
                        raise HTTPException(status_code=400, detail="Too many files in directory to scan.")
                    
                    file_path = os.path.join(root, file)
                    try:
                        # Use a size limit when reading files to prevent memory exhaustion (Billion Laughs/Large File)
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            # Read only the first 1MB of the file to prevent OOM on massive files
                            content = f.read(1024 * 1024)
                            if pattern.search(content):
                                rel_path = os.path.relpath(file_path, full_search_path)
                                matching_files.append(rel_path)
                    except Exception:
                        continue
        else:
            for entry in os.scandir(full_search_path):
                if entry.is_file():
                    files_scanned += 1
                    if files_scanned > MAX_FILES_TO_SCAN:
                        raise HTTPException(status_code=400, detail="Too many files in directory to scan.")
                    
                    try:
                        with open(entry.path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read(1024 * 1024)
                            if pattern.search(content):
                                matching_files.append(entry.name)
                    except Exception:
                        continue
    except HTTPException:
        raise
    except Exception as e:
        # Generic error to avoid leaking internal system details (stack traces)
        raise HTTPException(status_code=500, detail="An internal server error occurred while searching files.")

    return SearchResponse(files=matching_files)

if __name__ == "__main__":
    if not os.path.exists(FILES_ROOT):
        os.makedirs(FILES_ROOT)
        
    uvicorn.run(app, host="0.0.0.0", port=5000)