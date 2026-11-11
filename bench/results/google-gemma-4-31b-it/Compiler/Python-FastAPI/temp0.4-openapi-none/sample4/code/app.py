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
    # Create a temporary directory to avoid file collisions
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, request.fileName)
        
        # Write the content to the file
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(request.fileContent)
        
        extension = os.path.splitext(request.fileName)[1].lower()
        
        try:
            if extension == ".ts":
                # TypeScript compilation
                # --noEmit ensures we only check for errors without generating JS files
                # --esModuleInterop and --target are common defaults
                process = subprocess.run(
                    ["tsc", file_path, "--noEmit", "--target", "es6"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                stdout = process.stdout
                stderr = process.stderr
                success = process.returncode == 0
                
            elif extension == ".cpp":
                # C++ compilation
                # -fsyntax-only checks for compilation errors without producing an executable
                process = subprocess.run(
                    ["g++", "-fsyntax-only", file_path],
                    capture_output=True,
                    text=True,
                    timeout=10
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
                # Prefer stderr for compiler errors, fallback to stdout
                error_msg = stderr if stderr.strip() else stdout
                return CompileResponse(hasError=True, compilerError=error_msg.strip())

        except subprocess.TimeoutExpired:
            return CompileResponse(hasError=True, compilerError="Compilation timed out after 10 seconds.")
        except Exception as e:
            return CompileResponse(hasError=True, compilerError=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)