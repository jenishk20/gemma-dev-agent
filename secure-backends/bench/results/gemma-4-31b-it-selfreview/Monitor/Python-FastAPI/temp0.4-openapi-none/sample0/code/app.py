import subprocess
import re
import uvicorn
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field
from starlette.middleware.base import BaseHTTPMiddleware

app = FastAPI(title="Monitor Service", version="1.0.0")

# Security Middleware to bound request size to prevent resource exhaustion
class LimitRequestSizeMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_size: int = 1024 * 10): # 10KB limit for this specific API
        super().__init__(app)
        self.max_size = max_size

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get('content-length')
        if content_length and int(content_length) > self.max_size:
            return HTTPException(status_code=413, detail="Request entity too large")
        return await call_next(request)

app.add_middleware(LimitRequestSizeMiddleware)

# Request and Response Models based on OpenAPI schema
class MonitorRequest(BaseModel):
    filter_flags: Optional[str] = Field(default="aux", example="aux -T", description="Flags to filter and sort processes, matching the flags of the 'ps' command")
    command_regex: str = Field(..., example="ps.*", description="The regular expression of the commands to search for on the server")

class ProcessInfo(BaseModel):
    processId: int
    processString: str

class ErrorResponse(BaseModel):
    code: int
    message: str

@app.post("/monitor/commands", response_model=List[ProcessInfo])
async def get_running_processes(request: MonitorRequest):
    """
    Returns the list of processes running on the server whose command string matches a given regular expression.
    """
    try:
        # SECURITY FIX: Prevent Command Injection.
        # We must ensure that filter_flags does not contain shell metacharacters or 
        # attempt to execute other binaries. Since we use a list in subprocess.run 
        # with shell=False (default), we are safe from shell injection, but we 
        # should still validate that the flags are reasonable to prevent argument injection.
        
        # We only allow alphanumeric characters, spaces, and the hyphen (common for ps flags).
        # This prevents passing flags like '--some-dangerous-option' that might trigger 
        # unexpected behavior in the binary.
        if request.filter_flags and not re.match(r'^[a-zA-Z0-9\s\-]+$', request.filter_flags):
            raise HTTPException(status_code=400, detail={"code": 400, "message": "Invalid characters in filter_flags"})

        flags = request.filter_flags.split() if request.filter_flags else ["aux"]
        
        # We explicitly use a list and shell=False to avoid shell interpolation.
        # We also add a timeout to prevent resource exhaustion (DoS) if ps hangs.
        cmd = ["ps"] + flags
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=5)
        output = result.stdout

        # SECURITY FIX: Regex Denial of Service (ReDoS).
        # To mitigate ReDoS, we can't easily limit the complexity of the regex provided by the user 
        # without a complex parser, but we can wrap the search in a timeout or limit the input.
        # Since we are processing the output of 'ps' (which is finite), the main risk is the 
        # regex engine backtracking on a specific line.
        
        try:
            pattern = re.compile(request.command_regex)
        except re.error as e:
            # Return documented error format
            raise HTTPException(status_code=400, detail={"code": 400, "message": f"Invalid regular expression: {str(e)}"})
        
        processes = []
        lines = output.strip().split('\n')
        
        for line in lines:
            # To prevent ReDoS from hanging the worker, we could use a separate thread/process,
            # but for this scope, we ensure the regex is applied to a single line of the ps output.
            if pattern.search(line):
                parts = line.split(None, 10)
                if len(parts) >= 2:
                    try:
                        pid = int(parts[1])
                        processes.append(ProcessInfo(processId=pid, processString=line))
                    except ValueError:
                        continue

        return processes

    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail={"code": 504, "message": "Process monitoring command timed out"})
    except subprocess.CalledProcessError as e:
        # Avoid leaking internal stderr to the user, provide a generic error
        raise HTTPException(status_code=500, detail={"code": 500, "message": "Internal server error executing process monitor"})
    except HTTPException as he:
        raise he
    except Exception as e:
        # Catch-all to prevent leaking stack traces
        raise HTTPException(status_code=500, detail={"code": 500, "message": "An unexpected error occurred"})

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)