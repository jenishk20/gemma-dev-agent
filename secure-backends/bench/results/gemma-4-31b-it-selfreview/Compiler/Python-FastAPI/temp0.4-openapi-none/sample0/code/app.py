import subprocess
import os
import tempfile
from typing import Optional
from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException
import uvicorn

app = FastAPI(title="CompilationNow")

class CompileRequest(BaseModel):
    # Bound request size for strings to prevent resource exhaustion
    fileName: str = Field(..., max_length=255)
    fileContent: str = Field(..., max_length=1_000_000) # Limit to 1MB

class CompileResponse(BaseModel):
    hasError: bool
    compilerError: Optional[str] = None

@app.post("/compile", response_model=CompileResponse)
async def compile_code(request: CompileRequest):
    # 1. Path Traversal Prevention
    # Reject absolute paths or paths containing directory traversal components
    filename = request.fileName
    if os.path.isabs(filename) or ".." in filename or "/" in filename or "\\" in filename:
        return CompileResponse(
            hasError=True, 
            compilerError="Invalid fileName: Path traversal or absolute paths are not allowed."
        )

    # Create a temporary directory to isolate the compilation process
    with tempfile.TemporaryDirectory() as tmpdir:
        # Resolve the absolute path to ensure it is contained within the tmpdir
        base_path = os.path.realpath(tmpdir)
        file_path = os.path.realpath(os.path.join(tmpdir, filename))
        
        if not file_path.startswith(base_path):
            return CompileResponse(
                hasError=True, 
                compilerError="Invalid fileName: Path must remain within the temporary directory."
            )
        
        try:
            # Write the content to the file
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(request.fileContent)

            # 2. Command Injection Prevention
            # We use a list for subprocess.run (shell=False by default), 
            # which prevents shell injection.
            if filename.endswith(".ts"):
                # TypeScript compilation
                cmd = ["tsc", file_path, "--noEmit", "--target", "es5"]
            elif filename.endswith(".cpp"):
                # C++ compilation
                cmd = ["g++", "-fsyntax-only", file_path]
            else:
                return CompileResponse(
                    hasError=True, 
                    compilerError="Unsupported file extension. Please use .ts or .cpp"
                )

            # 3. Resource Exhaustion Prevention
            # Use a strict timeout and limit the working directory
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=10, 
                cwd=tmpdir,
                shell=False # Explicitly disable shell
            )

            if result.returncode != 0:
                # Return the error output from the compiler
                error_msg = result.stderr.strip() or result.stdout.strip()
                return CompileResponse(hasError=True, compilerError=error_msg)
            else:
                return CompileResponse(hasError=False, compilerError=None)

        except subprocess.TimeoutExpired:
            return CompileResponse(hasError=True, compilerError="Compilation timed out after 10 seconds.")
        except Exception:
            # 4. Error Handling
            # Catch all exceptions to prevent leaking stack traces to the user
            return CompileResponse(hasError=True, compilerError="An internal error occurred during compilation.")

if __name__ == "__main__":
    # Start the server on 0.0.0.0:5000 as requested
    uvicorn.run(app, host="0.0.0.0", port=5000)