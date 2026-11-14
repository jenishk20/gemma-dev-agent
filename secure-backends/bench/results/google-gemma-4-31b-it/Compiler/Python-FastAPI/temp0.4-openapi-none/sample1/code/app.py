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
        
        with open(file_path, "w") as f:
            f.write(request.fileContent)

        extension = os.path.splitext(request.fileName)[1].lower()
        
        try:
            if extension == ".ts":
                # Use tsc (TypeScript Compiler)
                # --noEmit prevents generating .js files, we only care about type checking/errors
                # --outFile is used to satisfy some tsc versions, but --noEmit is cleaner
                process = subprocess.run(
                    ["tsc", file_path, "--noEmit", "--target", "es5"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if process.returncode != 0 or process.stdout:
                    # tsc often prints errors to stdout rather than stderr
                    error_msg = process.stdout if process.stdout else process.stderr
                    return CompileResponse(hasError=True, compilerError=error_msg.strip())
                
            elif extension == ".cpp":
                # Use g++ for C++ compilation
                # -x c++ ensures it treats the file as C++ even if extension is weird
                process = subprocess.run(
                    ["g++", file_path, "-o", os.path.join(tmpdir, "out")],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if process.returncode != 0:
                    return CompileResponse(hasError=True, compilerError=process.stderr.strip())
            
            else:
                return CompileResponse(hasError=True, compilerError="Unsupported file extension. Please use .ts or .cpp")

            return CompileResponse(hasError=False, compilerError=None)

        except subprocess.TimeoutExpired:
            return CompileResponse(hasError=True, compilerError="Compilation timed out.")
        except Exception as e:
            return CompileResponse(hasError=True, compilerError=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)