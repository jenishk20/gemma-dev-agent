import subprocess
import os
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
    # Create a temporary directory to avoid file collisions and cleanup
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, request.fileName)
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(request.fileContent)

        # Determine compiler based on extension
        if request.fileName.endswith(".cpp"):
            # C++ Compilation
            # -x c++ ensures it treats the file as C++ even if extension is weird
            # We use g++ and capture stderr
            cmd = ["g++", file_path, "-o", os.path.join(tmpdir, "out")]
            try:
                result = subprocess.run(
                    cmd, 
                    capture_output=True, 
                    text=True, 
                    timeout=10
                )
                if result.returncode != 0:
                    return CompileResponse(hasError=True, compilerError=result.stderr.strip())
                return CompileResponse(hasError=False, compilerError=None)
            except subprocess.TimeoutExpired:
                return CompileResponse(hasError=True, compilerError="Compilation timed out.")
            except Exception as e:
                return CompileResponse(hasError=True, compilerError=str(e))

        elif request.fileName.endswith(".ts"):
            # TypeScript Compilation
            # tsc is installed globally. We use --noEmit to just check for errors.
            # --target es5 is a safe default.
            cmd = ["tsc", file_path, "--noEmit", "--target", "es5"]
            try:
                result = subprocess.run(
                    cmd, 
                    capture_output=True, 
                    text=True, 
                    timeout=10
                )
                if result.returncode != 0:
                    # tsc outputs errors to stdout usually, but we check both
                    error_msg = result.stdout.strip() or result.stderr.strip()
                    return CompileResponse(hasError=True, compilerError=error_msg)
                return CompileResponse(hasError=False, compilerError=None)
            except subprocess.TimeoutExpired:
                return CompileResponse(hasError=True, compilerError="Compilation timed out.")
            except Exception as e:
                return CompileResponse(hasError=True, compilerError=str(e))
        
        else:
            return CompileResponse(hasError=True, compilerError="Unsupported file extension. Please use .cpp or .ts")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)