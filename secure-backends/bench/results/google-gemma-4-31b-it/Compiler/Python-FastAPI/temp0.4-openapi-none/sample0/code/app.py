import subprocess
import os
import tempfile
import shutil
from typing import Optional
from pydantic import BaseModel
from fastapi import FastAPI
import uvicorn

app = FastAPI(title="CompilationNow")

class CompileRequest(BaseModel):
    fileName: str
    fileContent: str

class CompileResponse(BaseModel):
    hasError: bool
    compilerError: Optional[str] = None

@app.post("/compile", response_model=CompileResponse)
async def compile_code(request: CompileRequest):
    # Create a temporary directory to isolate the compilation process
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, request.fileName)
        
        # Write the content to the file
        with open(file_path, "w") as f:
            f.write(request.fileContent)

        # Determine the compiler based on file extension
        if request.fileName.endswith(".ts"):
            # TypeScript compilation
            # We use --noEmit to check for errors without generating JS files
            # --target es5 is a safe default
            cmd = ["tsc", file_path, "--noEmit", "--target", "es5"]
        elif request.fileName.endswith(".cpp"):
            # C++ compilation
            # -fsyntax-only checks for compilation errors without producing an executable
            cmd = ["g++", "-fsyntax-only", file_path]
        else:
            return CompileResponse(
                hasError=True, 
                compilerError="Unsupported file extension. Please use .ts or .cpp"
            )

        try:
            # Run the compiler command
            # capture_output=True captures stdout and stderr
            # text=True returns strings instead of bytes
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=10, 
                cwd=tmpdir
            )

            if result.returncode != 0:
                # Return the error output from the compiler
                # Prefer stderr, fallback to stdout
                error_msg = result.stderr.strip() or result.stdout.strip()
                return CompileResponse(hasError=True, compilerError=error_msg)
            else:
                return CompileResponse(hasError=False, compilerError=None)

        except subprocess.TimeoutExpired:
            return CompileResponse(hasError=True, compilerError="Compilation timed out after 10 seconds.")
        except Exception as e:
            return CompileResponse(hasError=True, compilerError=f"Internal compiler error: {str(e)}")

if __name__ == "__main__":
    # Start the server on 0.0.0.0:5000 as requested
    uvicorn.run(app, host="0.0.0.0", port=5000)