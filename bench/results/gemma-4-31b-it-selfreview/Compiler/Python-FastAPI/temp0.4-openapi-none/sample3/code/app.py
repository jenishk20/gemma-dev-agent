import os
import subprocess
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
    # --- SECURITY FIX: Path Traversal Prevention ---
    # 1. Reject absolute paths
    if os.path.isabs(request.fileName):
        return CompileResponse(
            hasError=True, 
            compilerError="Invalid fileName: Absolute paths are not allowed."
        )
    
    # 2. Reject path traversal components (..)
    # We normalize the path and check if it attempts to escape the current directory
    normalized_name = os.path.normpath(request.fileName)
    if normalized_name.startswith("..") or ".." in normalized_name.split(os.sep):
        return CompileResponse(
            hasError=True, 
            compilerError="Invalid fileName: Path traversal is not allowed."
        )

    # Create a temporary directory to isolate file operations
    with tempfile.TemporaryDirectory() as tmpdir:
        # Ensure the final path is strictly inside the temp directory
        file_path = os.path.join(tmpdir, normalized_name)
        
        # Double check that the resolved path is still within tmpdir
        if not os.path.abspath(file_path).startswith(os.path.abspath(tmpdir)):
            return CompileResponse(
                hasError=True, 
                compilerError="Invalid fileName: Path must be within the sandbox."
            )

        try:
            # Write the user content to the file
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(request.fileContent)
            
            ext = os.path.splitext(normalized_name)[1].lower()
            
            # --- SECURITY FIX: Shell Injection Prevention ---
            # We use a list of arguments with shell=False (default in subprocess.run)
            # to ensure input is not interpreted by a shell.
            if ext == ".ts":
                # TypeScript compilation
                process = subprocess.run(
                    ["tsc", file_path, "--noEmit", "--esModuleInterop"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    shell=False 
                )
                error_output = process.stdout if process.stdout else process.stderr
            elif ext == ".cpp":
                # C++ compilation
                # Use a fixed output filename inside the temp dir to prevent output path injection
                out_path = os.path.join(tmpdir, "out.bin")
                process = subprocess.run(
                    ["g++", file_path, "-o", out_path],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    shell=False
                )
                error_output = process.stderr
            else:
                return CompileResponse(
                    hasError=True, 
                    compilerError=f"Unsupported file extension: {ext}. Please use .ts or .cpp"
                )

            if process.returncode != 0:
                # Return the compiler error, stripping potential control characters
                # to prevent log injection or terminal manipulation in the client.
                sanitized_error = error_output.strip().replace('\r', '').replace('\n', ' ') if error_output else "Unknown compilation error"
                return CompileResponse(
                    hasError=True, 
                    compilerError=sanitized_error
                )
            
            return CompileResponse(hasError=False, compilerError=None)

        except subprocess.TimeoutExpired:
            return CompileResponse(hasError=True, compilerError="Compilation timed out after 10 seconds")
        except Exception as e:
            # --- SECURITY FIX: Error Handling ---
            # Do not leak internal stack traces or system paths in the response.
            return CompileResponse(hasError=True, compilerError="An internal error occurred during compilation.")

if __name__ == "__main__":
    import uvicorn
    # Port 0.0.0.0:5000 as requested
    uvicorn.run(app, host="0.0.0.0", port=5000)