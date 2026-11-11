import subprocess
import os
import tempfile
from typing import Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="CompilationNow")

class CompileRequest(BaseModel):
    # Limit input size to prevent resource exhaustion (DoS)
    fileName: str = Field(..., max_length=255)
    fileContent: str = Field(..., max_length=1_000_000) # 1MB limit

class CompileResponse(BaseModel):
    hasError: bool
    compilerError: Optional[str] = None

@app.post("/compile", response_model=CompileResponse)
async def compile_code(request: CompileRequest):
    # 1. Path Traversal Prevention
    # Reject absolute paths or paths containing '..'
    filename = request.fileName
    if os.path.isabs(filename) or ".." in filename or "/" in filename or "\\" in filename:
        return CompileResponse(hasError=True, compilerError="Invalid fileName: Path traversal or absolute paths are not allowed.")

    # Create a temporary directory to isolate files
    with tempfile.TemporaryDirectory() as tmpdir:
        # Resolve the final path and ensure it is strictly inside the tmpdir
        file_path = os.path.join(tmpdir, filename)
        if not os.path.abspath(file_path).startswith(os.path.abspath(tmpdir)):
            return CompileResponse(hasError=True, compilerError="Invalid fileName: Path resolution error.")
        
        try:
            # Write content safely
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(request.fileContent)

            extension = os.path.splitext(filename)[1].lower()
            
            # 2. Command Injection Prevention
            # We use a list for arguments and shell=False (default) to avoid shell interpolation.
            if extension == ".ts":
                # Use tsc (TypeScript Compiler)
                process = subprocess.run(
                    ["tsc", file_path, "--noEmit", "--target", "es5"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    shell=False 
                )
                
                if process.returncode != 0 or process.stdout:
                    error_msg = process.stdout if process.stdout else process.stderr
                    return CompileResponse(hasError=True, compilerError=error_msg.strip())
                
            elif extension == ".cpp":
                # Use g++ for C++ compilation
                # Output file is placed inside the secure tmpdir
                out_path = os.path.join(tmpdir, "out.bin")
                process = subprocess.run(
                    ["g++", file_path, "-o", out_path],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    shell=False
                )
                
                if process.returncode != 0:
                    return CompileResponse(hasError=True, compilerError=process.stderr.strip())
            
            else:
                return CompileResponse(hasError=True, compilerError="Unsupported file extension. Please use .ts or .cpp")

            return CompileResponse(hasError=False, compilerError=None)

        except subprocess.TimeoutExpired:
            return CompileResponse(hasError=True, compilerError="Compilation timed out.")
        except Exception as e:
            # 3. Error Handling
            # Return a generic error message to avoid leaking internal stack traces or system paths
            return CompileResponse(hasError=True, compilerError="An internal error occurred during compilation.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)