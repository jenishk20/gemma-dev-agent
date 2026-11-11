import subprocess
import os
import tempfile
from typing import Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="CompilationNow")

# Resource exhaustion limits
MAX_FILE_SIZE = 1 * 1024 * 1024  # 1MB limit for code snippets
MAX_FILENAME_LENGTH = 255

class CompileRequest(BaseModel):
    # Limit input sizes to prevent resource exhaustion
    fileName: str = Field(..., max_length=MAX_FILENAME_LENGTH)
    fileContent: str = Field(..., max_length=MAX_FILE_SIZE)

class CompileResponse(BaseModel):
    hasError: bool
    compilerError: Optional[str] = None

@app.post("/compile", response_model=CompileResponse)
async def compile_code(request: CompileRequest):
    # 1. Path Traversal Prevention
    # Reject absolute paths and paths containing '..'
    filename = request.fileName
    if os.path.isabs(filename) or ".." in filename:
        return CompileResponse(
            hasError=True, 
            compilerError="Invalid fileName: Path traversal or absolute paths are not allowed."
        )

    # Create a temporary directory to isolate the process
    with tempfile.TemporaryDirectory() as tmpdir:
        # Resolve the final path and verify it is still within the tmpdir
        # This prevents bypasses using complex naming schemes
        safe_path = os.path.normpath(os.path.join(tmpdir, filename))
        if not safe_path.startswith(os.path.abspath(tmpdir)):
            return CompileResponse(
                hasError=True, 
                compilerError="Invalid fileName: Path must remain within the sandbox."
            )
        
        try:
            # Write the content to the file
            # Using utf-8 and limiting size via Pydantic Field
            with open(safe_path, "w", encoding="utf-8") as f:
                f.write(request.fileContent)
        except Exception as e:
            return CompileResponse(hasError=True, compilerError=f"File system error: {str(e)}")
        
        extension = os.path.splitext(filename)[1].lower()
        
        try:
            # 2. Shell Injection Prevention
            # subprocess.run is called with a list (shell=False by default), 
            # preventing shell command injection.
            if extension == ".ts":
                # TypeScript compilation
                process = subprocess.run(
                    ["tsc", safe_path, "--noEmit", "--target", "es6"],
                    capture_output=True,
                    text=True,
                    timeout=10, # Prevent resource exhaustion (CPU/Time)
                    shell=False 
                )
                stdout = process.stdout
                stderr = process.stderr
                success = process.returncode == 0
                
            elif extension == ".cpp":
                # C++ compilation
                # -fsyntax-only avoids generating binary artifacts (prevents disk exhaustion)
                process = subprocess.run(
                    ["g++", "-fsyntax-only", safe_path],
                    capture_output=True,
                    text=True,
                    timeout=10, # Prevent resource exhaustion (CPU/Time)
                    shell=False
                )
                stdout = process.stdout
                stderr = process.stderr
                success = process.returncode == 0
            else:
                return CompileResponse(
                    hasError=True, 
                    compilerError=f"Unsupported file extension: {extension}. Please use .ts or .cpp"
                )

            if success:
                return CompileResponse(hasError=False, compilerError=None)
            else:
                # 3. Error Handling & Information Leakage
                # We return the compiler's output as specified, but strip 
                # excessive whitespace to prevent log/response bloating.
                error_msg = stderr if stderr.strip() else stdout
                return CompileResponse(hasError=True, compilerError=error_msg.strip())

        except subprocess.TimeoutExpired:
            return CompileResponse(hasError=True, compilerError="Compilation timed out after 10 seconds.")
        except Exception as e:
            # Catch-all to prevent leaking internal stack traces to the user
            return CompileResponse(hasError=True, compilerError="An internal error occurred during compilation.")

if __name__ == "__main__":
    import uvicorn
    # Start server on 0.0.0.0:5000 as requested
    uvicorn.run(app, host="0.0.0.0", port=5000)