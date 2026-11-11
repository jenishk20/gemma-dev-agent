import os
import subprocess
import tempfile
import shutil
from typing import Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import uvicorn

app = FastAPI(title="CompilationNow")

class CompileRequest(BaseModel):
    fileName: str = Field(..., example="main.ts")
    fileContent: str = Field(..., example="let x = 2 * 15;")

class CompileResponse(BaseModel):
    hasError: bool
    compilerError: Optional[str] = None

def run_compiler(file_name: str, content: str, temp_dir: str):
    """
    Handles the logic of writing the file and calling the appropriate compiler.
    """
    # Security: Prevent path traversal by taking only the basename of the filename
    safe_name = os.path.basename(file_name)
    file_path = os.path.join(temp_dir, safe_name)
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

    if safe_name.endswith(".ts"):
        # TypeScript compilation
        # We use --noEmit to check for errors without generating js files
        # and --target es5 for general compatibility
        cmd = ["tsc", file_path, "--noEmit", "--target", "es5"]
    elif safe_name.endswith(".cpp"):
        # C++ compilation
        # -fsyntax-only checks for compilation errors without producing an executable
        cmd = ["g++", "-fsyntax-only", file_path]
    else:
        raise ValueError("Unsupported file extension. Please use .ts or .cpp")

    try:
        # Run the compiler. capture_output=True captures stdout and stderr.
        # timeout is set to prevent infinite loops or hanging processes.
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            timeout=10,
            cwd=temp_dir
        )
        
        if result.returncode != 0:
            # Return the combined output as the error message
            error_msg = result.stderr if result.stderr else result.stdout
            return True, error_msg.strip()
        else:
            return False, None
            
    except subprocess.TimeoutExpired:
        return True, "Compilation timed out after 10 seconds."
    except Exception as e:
        return True, f"Internal compiler error: {str(e)}"

@app.post("/compile", response_model=CompileResponse)
async def compile_code(request: CompileRequest):
    # Create a temporary directory to isolate the compilation process
    temp_dir = tempfile.mkdtemp()
    try:
        has_error, error_msg = run_compiler(request.fileName, request.fileContent, temp_dir)
        return CompileResponse(hasError=has_error, compilerError=error_msg)
    except ValueError as ve:
        # Handle unsupported file extensions
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        # Handle unexpected errors
        raise HTTPException(status_code=500, detail="An internal server error occurred.")
    finally:
        # Clean up the temporary directory
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    # Start the server on 0.0.0.0:5000 as requested
    uvicorn.run(app, host="0.0.0.0", port=5000)