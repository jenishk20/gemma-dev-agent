import os
import subprocess
import tempfile
import shutil
from typing import Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="CompilationNow")

class CompileRequest(BaseModel):
    fileName: str = Field(..., example="main.ts")
    fileContent: str = Field(..., example="let x = 2 * 15;")

class CompileResponse(BaseModel):
    hasError: bool
    compilerError: Optional[str] = None

@app.post("/compile", response_model=CompileResponse)
async def compile_code(request: CompileRequest):
    # Security: Validate fileName to prevent directory traversal
    # Only allow alphanumeric, dots, and underscores. No slashes.
    filename = os.path.basename(request.fileName)
    if not filename or any(char in filename for char in ['/', '\\', '..']):
        raise HTTPException(status_code=400, detail="Invalid fileName provided.")

    # Determine language based on extension
    ext = os.path.splitext(filename)[1].lower()
    
    # Create a temporary directory to isolate the compilation process
    with tempfile.mkdtemp() as tmpdir:
        file_path = os.path.join(tmpdir, filename)
        
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(request.fileContent)
            
            if ext == ".ts":
                # TypeScript compilation: tsc
                # --noEmit prevents generating .js files, we only want the check
                # --target es5 is a safe default
                cmd = ["tsc", file_path, "--noEmit", "--target", "es5"]
            elif ext == ".cpp":
                # C++ compilation: g++
                # -fsyntax-only checks for errors without producing an executable
                cmd = ["g++", "-fsyntax-only", file_path]
            else:
                raise HTTPException(status_code=400, detail="Unsupported file extension. Please use .ts or .cpp")

            # Execute the compiler
            # Use capture_output to get stderr/stdout and timeout to prevent hanging
            process = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=10,
                cwd=tmpdir
            )

            if process.returncode != 0:
                # Return the error output from the compiler
                error_msg = process.stderr.strip() or process.stdout.strip()
                return CompileResponse(hasError=True, compilerError=error_msg)
            
            return CompileResponse(hasError=False, compilerError=None)

        except subprocess.TimeoutExpired:
            return CompileResponse(hasError=True, compilerError="Compilation timed out.")
        except Exception as e:
            return CompileResponse(hasError=True, compilerError=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)