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

def safe_filename(filename: str) -> str:
    """
    Basic sanitization to prevent directory traversal.
    Only allows alphanumeric, dots, and underscores.
    """
    return "".join(c for c in filename if c.isalnum() or c in "._-")

@app.post("/compile", response_model=CompileResponse)
async def compile_code(request: CompileRequest):
    # Sanitize filename to prevent path traversal
    safe_name = safe_filename(request.fileName)
    if not safe_name:
        raise HTTPException(status_code=400, detail="Invalid fileName provided.")

    # Create a temporary directory for the compilation process
    # This ensures isolation and prevents cluttering the system
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, safe_name)
        
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(request.fileContent)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to write file: {str(e)}")

        # Determine compiler based on extension
        if safe_name.endswith(".cpp"):
            # C++ Compilation: g++
            # We use -x c++ to ensure it treats it as C++ and avoid some extension-based issues
            # We limit the command to prevent shell injection by passing arguments as a list
            cmd = ["g++", file_path, "-o", os.path.join(tmpdir, "out")]
        elif safe_name.endswith(".ts"):
            # TypeScript Compilation: tsc
            # --noEmit is used because we only care about the compiler feedback/errors
            cmd = ["tsc", file_path, "--noEmit", "--esModuleInterop", "--target", "es5"]
        else:
            # If the extension is not supported, we treat it as a compilation error
            return CompileResponse(
                hasError=True, 
                compilerError="Unsupported file extension. Please use .cpp or .ts"
            )

        try:
            # Run the compiler. capture_output=True captures stdout and stderr.
            # timeout is set to prevent Denial of Service via infinite loops/heavy compilation
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=15,
                cwd=tmpdir
            )
            
            if result.returncode != 0:
                # Combine stderr and stdout as different compilers report errors in different streams
                error_msg = (result.stderr + "\n" + result.stdout).strip()
                return CompileResponse(hasError=True, compilerError=error_msg or "Unknown compilation error")
            
            return CompileResponse(hasError=False, compilerError=None)

        except subprocess.TimeoutExpired:
            return CompileResponse(hasError=True, compilerError="Compilation timed out after 15 seconds.")
        except Exception as e:
            return CompileResponse(hasError=True, compilerError=f"Internal compiler error: {str(e)}")

if __name__ == "__main__":
    # Start the server on 0.0.0.0:5000 as requested
    uvicorn.run(app, host="0.0.0.0", port=5000)