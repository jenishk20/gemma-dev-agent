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
    # Validate regex pattern
    try:
        pattern = re.compile(regex)
    except re.error as e:
        raise HTTPException(status_code=400, detail=f"Invalid regex pattern: {str(e)}")

    # Determine the base search path
    search_base = FILES_ROOT if not directory else os.path.join(FILES_ROOT, directory)
    
    # Security check: Ensure the search path is within the FILES_ROOT to prevent directory traversal
    if not os.path.abspath(search_base).startswith(FILES_ROOT):
        raise HTTPException(status_code=400, detail="Directory path is outside the allowed root directory.")

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
                    try:
                        with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            if pattern.search(content):
                                # Calculate path relative to the search_base as per schema
                                rel_path = os.path.relpath(full_path, search_base)
                                matching_files.append(rel_path)
                    except Exception:
                        # Skip files that cannot be read
                        continue
        else:
            # Non-recursive: only check files in the immediate directory
            for entry in os.scandir(search_base):
                if entry.is_file():
                    try:
                        with open(entry.path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            if pattern.search(content):
                                matching_files.append(entry.name)
                    except Exception:
                        continue
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

    return SearchResponse(files=matching_files)

if __name__ == "__main__":
    # Ensure the files root directory exists for the app to function
    if not os.path.exists(FILES_ROOT):
        os.makedirs(FILES_ROOT)
        
    uvicorn.run(app, host="0.0.0.0", port=5000)