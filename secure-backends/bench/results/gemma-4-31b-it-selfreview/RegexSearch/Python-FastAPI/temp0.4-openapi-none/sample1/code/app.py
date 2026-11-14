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

@app.get("/search", response_model=SearchResponse)
async def search_files(
    regex: str = Query(..., description="The regex pattern to match partially against file contents"),
    directory: Optional[str] = Query(None, description="The directory path to search files in, relative to the files root directory"),
    recursive: bool = Query(False, description="Whether to search recursively in subdirectories")
):
    # 1. Regex Resource Exhaustion (ReDoS) Protection
    # While Python's 're' doesn't have a built-in timeout, we can limit the complexity 
    # of the regex string length to prevent extremely long patterns.
    if len(regex) > 1000:
        raise HTTPException(status_code=400, detail="Regex pattern is too long")

    try:
        pattern = re.compile(regex)
    except re.error as e:
        raise HTTPException(status_code=400, detail=f"Invalid regex pattern: {str(e)}")

    # 2. Path Traversal Prevention
    # We must ensure that the resulting path is strictly within FILES_ROOT.
    search_base = FILES_ROOT
    if directory:
        # Reject absolute paths to prevent escaping the root
        if os.path.isabs(directory):
            raise HTTPException(status_code=400, detail="Absolute paths are not allowed")
        
        # Join and resolve the absolute path
        requested_path = os.path.abspath(os.path.join(FILES_ROOT, directory))
        
        # Verify that the resolved path starts with the FILES_ROOT directory
        # commonpath returns the longest common sub-path of the sequences
        if os.path.commonpath([FILES_ROOT, requested_path]) != FILES_ROOT:
            raise HTTPException(status_code=400, detail="Invalid directory path: path traversal detected")
        
        search_base = requested_path
        
        if not os.path.exists(search_base) or not os.path.isdir(search_base):
            raise HTTPException(status_code=400, detail="Specified directory does not exist or is not a directory")

    matching_files = []

    try:
        # 3. Resource Exhaustion (File System/Memory)
        # We limit the number of files scanned and the size of files read to prevent DoS.
        MAX_FILES_TO_SCAN = 10000
        MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB limit per file
        files_scanned = 0

        if recursive:
            for root, dirs, files in os.walk(search_base):
                for file in files:
                    files_scanned += 1
                    if files_scanned > MAX_FILES_TO_SCAN:
                        break
                    
                    file_path = os.path.join(root, file)
                    try:
                        # Check file size before reading to prevent memory exhaustion
                        if os.path.getsize(file_path) > MAX_FILE_SIZE:
                            continue
                            
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            if pattern.search(content):
                                rel_path = os.path.relpath(file_path, search_base if directory else FILES_ROOT)
                                matching_files.append(rel_path)
                    except (OSError, IOError):
                        continue 
                if files_scanned > MAX_FILES_TO_SCAN:
                    break
        else:
            if not os.path.exists(search_base):
                raise HTTPException(status_code=400, detail="Directory not found")
            
            with os.scandir(search_base) as entries:
                for entry in entries:
                    files_scanned += 1
                    if files_scanned > MAX_FILES_TO_SCAN:
                        break
                    if entry.is_file():
                        try:
                            if entry.stat().st_size > MAX_FILE_SIZE:
                                continue
                            with open(entry.path, 'r', encoding='utf-8', errors='ignore') as f:
                                content = f.read()
                                if pattern.search(content):
                                    matching_files.append(entry.name)
                        except (OSError, IOError):
                            continue

    except HTTPException:
        raise
    except Exception as e:
        # 4. Error Handling: Prevent leaking internal stack traces
        # We log the error internally (not implemented here) and return a generic 500.
        raise HTTPException(status_code=500, detail="An internal server error occurred")

    return SearchResponse(files=matching_files)

if __name__ == "__main__":
    # Ensure the files root exists
    if not os.path.exists(FILES_ROOT):
        os.makedirs(FILES_ROOT, exist_ok=True)
        
    uvicorn.run(app, host="0.0.0.0", port=5000)