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
    # Reject absolute paths or paths containing parent directory references
    filename = request.fileName
    if os.path.isabs(filename) or ".." in filename or filename.startswith("/") or filename.startswith("\\"):
        return CompileResponse(hasError=True, compilerError="Invalid fileName: Path traversal attempt detected.")

    # Ensure the filename is just a name, not a path
    filename = os.path.basename(filename)
    if not filename:
        return CompileResponse(hasError=True, compilerError="Invalid fileName: Filename cannot be empty.")

    # Create a temporary directory to isolate execution
    with tempfile.TemporaryDirectory() as tmpdir:
        # Resolve the absolute path of the intended file to verify it stays within tmpdir
        file_path = os.path.join(tmpdir, filename)
        # Double check that the resolved path is indeed inside the temporary directory
        if not os.path.abspath(file_path).startswith(os.path.abspath(tmpdir)):
            return CompileResponse(hasError=True, compilerError="Invalid fileName: Path resolution error.")

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(request.fileContent)
        except Exception as e:
            return CompileResponse(hasError=True, compilerError="Internal error writing file.")

        # 2. Command Injection Prevention
        # We use a list for subprocess.run and shell=False (default) to avoid shell interpolation.
        # We also implement strict timeouts to prevent resource exhaustion.
        
        if filename.endswith(".cpp"):
            # C++ Compilation
            # -o specifies the output binary location inside the tmpdir
            output_bin = os.path.join(tmpdir, "out.bin")
            cmd = ["g++", file_path, "-o", output_bin]
            try:
                result = subprocess.run(
                    cmd, 
                    capture_output=True, 
                    text=True, 
                    timeout=10,
                    shell=False # Explicitly disable shell
                )
                if result.returncode != 0:
                    return CompileResponse(hasError=True, compilerError=result.stderr.strip())
                return CompileResponse(hasError=False, compilerError=None)
            except subprocess.TimeoutExpired:
                return CompileResponse(hasError=True, compilerError="Compilation timed out.")
            except Exception:
                return CompileResponse(hasError=True, compilerError="An internal error occurred during C++ compilation.")

        elif filename.endswith(".ts"):
            # TypeScript Compilation
            # --noEmit prevents the creation of .js files, reducing disk I/O and cleanup needs
            cmd = ["tsc", file_path, "--noEmit", "--target", "es5"]
            try:
                result = subprocess.run(
                    cmd, 
                    capture_output=True, 
                    text=True, 
                    timeout=10,
                    shell=False # Explicitly disable shell
                )
                if result.returncode != 0:
                    error_msg = result.stdout.strip() or result.stderr.strip()
                    return CompileResponse(hasError=True, compilerError=error_msg)
                return CompileResponse(hasError=False, compilerError=None)
            except subprocess.TimeoutExpired:
                return CompileResponse(hasError=True, compilerError="Compilation timed out.")
            except Exception:
                return CompileResponse(hasError=True, compilerError="An internal error occurred during TypeScript compilation.")
        
        else:
            return CompileResponse(hasError=True, compilerError="Unsupported file extension. Please use .cpp or .ts")

if __name__ == "__main__":
    import uvicorn
    # Port 0.0.0.0:5000 as requested
    uvicorn.run(app, host="0.0.0.0", port=5000)