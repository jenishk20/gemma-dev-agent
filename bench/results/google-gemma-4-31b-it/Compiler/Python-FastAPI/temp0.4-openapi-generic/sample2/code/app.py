import os
import subprocess
import tempfile
import shutil
from typing import Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import uvicorn

app = FastAPI(title="CompilationNow")

class CompileRequest(BaseModel):
    fileName: str = Field(..., example="main.ts")
    fileContent: str = Field(..., example="let x = 2 * 15;")

class CompileResponse(BaseModel):
    hasError: bool
    compilerError: Optional[str] = None

def validate_filename(filename: str):
    """
    Basic security check to prevent path traversal attacks.
    """
    # Only allow alphanumeric, dots, and underscores. No slashes.
    forbidden = ['/', '\\', '..', ':', '$', '>', '<', '"']
    if any(char in filename for char in forbidden):
        raise ValueError("Invalid characters in filename")
    return filename

@app.post("/compile", response_model=CompileResponse)
async def compile_code(request: CompileRequest):
    try:
        # Validate filename to prevent directory traversal
        safe_filename = validate_filename(request.fileName)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Create a temporary directory to isolate the compilation process
    with tempfile.mkdtemp() as tmpdir:
        file_path = os.path.join(tmpdir, safe_filename)
        
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(request.fileContent)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to write file: {str(e)}")

        # Determine compiler based on extension
        if safe_filename.endswith(".cpp"):
            # C++ compilation: g++ -fsyntax-only checks for compilation errors without producing binary
            # Using -fsyntax-only is faster and safer for a feedback app
            cmd = ["g++", "-fsyntax-only", file_path]
        elif safe_filename.endswith(".ts"):
            # TypeScript compilation: tsc
            # --noEmit prevents generating .js files
            cmd = ["tsc", file_path, "--noEmit"]
        else:
            raise HTTPException(status_code=400, detail="Unsupported file extension. Please use .cpp or .ts")

        try:
            # Run the compiler. capture_output=True captures stdout and stderr.
            # timeout prevents infinite loops or hanging processes.
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=10
            )
            
            if result.returncode != 0:
                # Return the stderr if the compiler failed
                return CompileResponse(
                    hasError=True, 
                    compilerError=result.stderr.strip() or result.stdout.strip()
                )
            else:
                return CompileResponse(hasError=False, compilerError=None)
                
        except subprocess.TimeoutExpired:
            raise HTTPException(status_code=408, detail="Compilation timed out")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Internal compiler error: {str(e)}")

if __name__ == "__main__":
    # Start the server on 0.0.0.0:5000 as requested
    uvicorn.run(app, host="0.0.0.0", port=5000)