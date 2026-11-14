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

def sanitize_filename(filename: str) -> str:
    """
    Basic sanitization to prevent directory traversal attacks.
    Only allows alphanumeric characters, dots, and underscores.
    """
    # Remove any path components and keep only the base name
    base_name = os.path.basename(filename)
    # Filter characters to prevent shell injection or path traversal
    allowed_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-"
    sanitized = "".join(c for c in base_name if c in allowed_chars)
    if not sanitized:
        return "temp_file"
    return sanitized

@app.post("/compile", response_model=CompileResponse)
async def compile_code(request: CompileRequest):
    # Sanitize filename to prevent directory traversal
    safe_filename = sanitize_filename(request.fileName)
    
    # Create a temporary directory for the compilation process
    # This ensures we don't pollute the server root and provides isolation
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, safe_filename)
        
        try:
            # Write the content to the file
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(request.fileContent)
            
            # Determine compiler based on extension
            if safe_filename.endswith(".cpp"):
                # C++ Compilation: g++
                # -Wall: all warnings, -std=c++17: standard
                # We use a list for subprocess to avoid shell=True (security risk)
                process = subprocess.run(
                    ["g++", file_path, "-o", os.path.join(tmpdir, "out")],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
            elif safe_filename.endswith(".ts"):
                # TypeScript Compilation: tsc
                # tsc outputs to stdout/stderr
                process = subprocess.run(
                    ["tsc", file_path, "--noEmit", "--esModuleInterop", "false"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
            else:
                raise HTTPException(status_code=400, detail="Unsupported file extension. Please use .cpp or .ts")

            if process.returncode != 0:
                # Combine stderr and stdout as compilers vary in where they put errors
                error_msg = (process.stderr or "").strip() or (process.stdout or "").strip()
                return CompileResponse(hasError=True, compilerError=error_msg)
            
            return CompileResponse(hasError=False, compilerError=None)

        except subprocess.TimeoutExpired:
            raise HTTPException(status_code=504, detail="Compilation timed out")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    # Start the server on 0.0.0.0:5000 as requested
    uvicorn.run(app, host="0.0.0.0", port=5000)