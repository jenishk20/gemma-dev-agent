import os
import re
from pathlib import Path
from typing import List, Optional
from fastapi import FastAPI, Query, HTTPException
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="File Search API")

# Root directory for files
FILES_ROOT = Path("./files").resolve()

class SearchResponse(BaseModel):
    files: List[str]

@app.get("/search", response_model=SearchResponse)
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

    # 2. Resolve and Validate Directory Path
    # We use Path.joinpath and resolve to prevent directory traversal attacks (e.g., using ../..)
    search_base = FILES_ROOT
    if directory:
        # Join the root with the provided directory and resolve it
        target_dir = (FILES_ROOT / directory).resolve()
        
        # Security Check: Ensure the resolved path is still within the FILES_ROOT
        if not str(target_dir).startswith(str(FILES_ROOT)):
            raise HTTPException(status_code=400, detail="Directory path is outside the allowed files root.")
        
        if not target_dir.is_dir():
            raise HTTPException(status_code=400, detail="The specified directory does not exist or is not a directory.")
        
        search_base = target_dir

    matching_files = []

    try:
        # 3. Iterate through files
        # Use rglob for recursive search, glob for non-recursive
        search_pattern = "**/*" if recursive else "*"
        
        for path in search_base.glob(search_pattern):
            if path.is_file():
                try:
                    # We read the file content. For very large files, this could be a memory issue,
                    # but given the constraints and "no streaming", we read the text.
                    # We use errors='ignore' to handle binary files or encoding issues gracefully.
                    content = path.read_text(encoding='utf-8', errors='ignore')
                    if pattern.search(content):
                        # Calculate path relative to the search_base as per requirements
                        relative_path = str(path.relative_to(search_base))
                        matching_files.append(relative_path)
                except Exception:
                    # Skip files that cannot be read
                    continue
                    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

    return SearchResponse(files=matching_files)

if __name__ == "__main__":
    # Ensure the root files directory exists so the app doesn't crash on startup
    FILES_ROOT.mkdir(parents=True, exist_ok=True)
    uvicorn.run(app, host="0.0.0.0", port=5000)