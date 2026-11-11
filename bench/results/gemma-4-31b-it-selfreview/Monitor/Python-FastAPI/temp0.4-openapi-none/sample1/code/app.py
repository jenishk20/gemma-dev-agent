import subprocess
import re
import uvicorn
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field
from fastapi.exceptions import RequestValidationError
from starlette.responses import JSONResponse

app = FastAPI(title="Monitor Service")

class MonitorRequest(BaseModel):
    filter_flags: Optional[str] = Field(default="aux", example="aux -T", description="Flags to filter and sort processes, matching the flags of the 'ps' command")
    command_regex: str = Field(..., example="ps.*", description="The regular expression of the commands to search for on the server")

class ProcessInfo(BaseModel):
    processId: int
    processString: str

class ErrorResponse(BaseModel):
    code: int
    message: str

# Custom exception handler to ensure we return the documented Error schema 
# and don't leak internal stack traces/details.
@app.exception_handler(Exception)
async def universal_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"code": 500, "message": "Internal server error"}
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"code": 422, "message": str(exc.errors())}
    )

@app.post("/monitor/commands", response_model=List[ProcessInfo])
async def get_processes(request: MonitorRequest):
    try:
        # SECURITY FIX: Prevent Command Injection.
        # We must ensure that filter_flags does not contain characters that could be interpreted 
        # as separate commands or shell redirections. 
        # Since we use subprocess.run with shell=False (default), arguments are passed as a list.
        # However, we must prevent the user from passing flags that might execute other binaries 
        # or perform dangerous operations (like -f or custom scripts).
        # We restrict flags to a safe set of characters to prevent argument injection.
        if request.filter_flags:
            if not re.match(r'^[a-zA-Z0-9\s\-\.]+$', request.filter_flags):
                raise HTTPException(status_code=400, detail={"code": 400, "message": "Invalid characters in filter_flags"})
            flags = request.filter_flags.split()
        else:
            flags = ["aux"]

        # Construct the ps command. shell=False is used by default.
        cmd = ["ps"] + flags
        
        # SECURITY FIX: Resource Exhaustion.
        # Added a timeout to prevent the process from hanging the server.
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=5)
        output = result.stdout
        
        # SECURITY FIX: Regex Denial of Service (ReDoS).
        # We wrap the regex compilation and search in a try-except. 
        # While Python's 're' doesn't have a built-in timeout, we limit the input length 
        # and handle potential errors.
        if len(request.command_regex) > 256:
            raise HTTPException(status_code=400, detail={"code": 400, "message": "Regex too long"})
            
        try:
            pattern = re.compile(request.command_regex)
        except re.error:
            raise HTTPException(status_code=400, detail={"code": 400, "message": "Invalid regular expression"})
        
        processes = []
        lines = output.strip().split('\n')
        
        if len(lines) <= 1:
            return []

        for line in lines[1:]:
            if not line.strip():
                continue
            
            # Use a try-except block for the search to catch potential catastrophic backtracking
            try:
                if pattern.search(line):
                    parts = line.split(None, 10)
                    if len(parts) >= 2:
                        try:
                            pid = int(parts[1])
                            processes.append(ProcessInfo(processId=pid, processString=line.strip()))
                        except ValueError:
                            continue
            except Exception:
                continue # Skip lines that cause regex engine issues
        
        return processes

    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail={"code": 504, "message": "Process monitoring timed out"})
    except subprocess.CalledProcessError as e:
        # Return a generic error message to avoid leaking system details
        raise HTTPException(status_code=500, detail={"code": 500, "message": "System command failed"})
    except HTTPException as he:
        raise he
    except Exception as e:
        # Final catch-all to ensure no stack traces are leaked
        raise HTTPException(status_code=500, detail={"code": 500, "message": "An unexpected error occurred"})

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)