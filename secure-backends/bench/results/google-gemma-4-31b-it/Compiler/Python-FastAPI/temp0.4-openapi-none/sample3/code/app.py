import os
import subprocess
import tempfile
import shutil
from typing import Optional
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="CompilationNow")

class CompileRequest(BaseModel):
    fileName: str
    fileContent: str

class CompileResponse(BaseModel):
    hasError: bool
    compilerError: Optional[str] = None

@app.post("/compile", response_model=CompileResponse)
async def compile_code(request: CompileRequest):
    # Create a temporary directory to avoid filename collisions and clutter
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, request.fileName)
        
        # Write the user content to the file
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(request.fileContent)
        
        # Determine compiler based on file extension
        ext = os.path.splitext(request.fileName)[1].lower()
        
        try:
            if ext == ".ts":
                # TypeScript compilation
                # tsc returns non-zero on errors. We capture stderr and stdout.
                process = subprocess.run(
                    ["tsc", file_path, "--noEmit", "--esModuleInterop"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                # tsc often outputs errors to stdout
                error_output = process.stdout if process.stdout else process.stderr
            elif ext == ".cpp":
                # C++ compilation
                process = subprocess.run(
                    ["g++", file_path, "-o", os.path.join(tmpdir, "out")],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                error_output = process.stderr
            else:
                return CompileResponse(
                    hasError=True, 
                    compilerError=f"Unsupported file extension: {ext}. Please use .ts or .cpp"
                )

            if process.returncode != 0:
                return CompileResponse(
                    hasError=True, 
                    compilerError=error_output.strip() if error_output else "Unknown compilation error"
                )
            
            return CompileResponse(hasError=False, compilerError=None)

        except subprocess.TimeoutExpired:
            return CompileResponse(hasError=True, compilerError="Compilation timed out after 10 seconds")
        except Exception as e:
            return CompileResponse(hasError=True, compilerError=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)