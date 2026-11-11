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

@app.get("/search", response_model=SearchResponse)
async def search_files(
    regex: str = Query(..., description="The regex pattern to match partially against file contents"),
    directory: Optional[str] = Query(None, description="The directory path to search files in, relative to the files root directory"),
    recursive: bool = Query(False, description="Whether to search recursively in subdirectories")
):
    # 1. Regex Denial of Service (ReDoS) Mitigation
    # While Python's 're' doesn't have a built-in timeout, we can't easily wrap it.
    # However, we must ensure the regex is valid.
    try:
        pattern = re.compile(regex)
    except re.error as e:
        raise HTTPException(status_code=400, detail=f"Invalid regex pattern: {str(e)}")

    # 2. Path Traversal Mitigation
    # Reject absolute paths or paths containing '..' to prevent escaping the root
    if directory:
        if os.path.isabs(directory) or ".." in directory:
            raise HTTPException(status_code=400, detail="Invalid directory path: absolute paths and '..' are not allowed.")
        
        search_base = os.path.abspath(os.path.join(FILES_ROOT, directory))
    else:
        search_base = FILES_ROOT

    # Final verification that the resolved path is still within FILES_ROOT
    if not search_base.startswith(FILES_ROOT):
        raise HTTPException(status_code=400, detail="Directory path is outside the allowed root directory.")

    if not os.path.exists(search_base):
        raise HTTPException(status_code=400, detail="Specified directory does not exist.")
    
    if not os.path.isdir(search_base):
        raise HTTPException(status_code=400, detail="Specified path is not a directory.")

    matching_files = []

    try:
        # 3. Resource Exhaustion Mitigation
        # We limit the number of files processed to prevent CPU/Memory exhaustion
        MAX_FILES_TO_SCAN = 10000 
        files_scanned = 0

        if recursive:
            for root, dirs, files in os.walk(search_base):
                for file in files:
                    files_scanned += 1
                    if files_scanned > MAX_FILES_TO_SCAN:
                        break
                    
                    full_path = os.path.join(root, file)
                    try:
                        # Limit read size to prevent memory exhaustion from huge files
                        with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read(10 * 1024 * 1024) # Read up to 10MB
                            if pattern.search(content):
                                rel_path = os.path.relpath(full_path, search_base)
                                matching_files.append(rel_path)
                    except Exception:
                        continue
                if files_scanned > MAX_FILES_TO_SCAN:
                    break
        else:
            for entry in os.scandir(search_base):
                if entry.is_file():
                    files_scanned += 1
                    if files_scanned > MAX_FILES_TO_SCAN:
                        break
                    try:
                        with open(entry.path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read(10 * 1024 * 1024)
                            if pattern.search(content):
                                matching_files.append(entry.name)
                    except Exception:
                        continue
    except Exception as e:
        # 4. Error Handling: Do not leak internal stack traces
        raise HTTPException(status_code=500, detail="An internal server error occurred while searching files.")

    return SearchResponse(files=matching_files)

if __name__ == "__main__":
    if not os.path.exists(FILES_ROOT):
        os.makedirs(FILES_ROOT)
        
    uvicorn.run(app, host="0.0.0.0", port=5000)