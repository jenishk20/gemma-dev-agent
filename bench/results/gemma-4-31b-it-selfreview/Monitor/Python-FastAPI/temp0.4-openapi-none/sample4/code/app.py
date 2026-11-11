import subprocess
import re
import uvicorn
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field
from fastapi.responses import JSONResponse

app = FastAPI(title="Monitor Service")

class MonitorRequest(BaseModel):
    filter_flags: Optional[str] = Field(default="aux", description="Flags to filter and sort processes, matching the flags of the 'ps' command")
    command_regex: str = Field(..., description="The regular expression of the commands to search for on the server")

class ProcessInfo(BaseModel):
    processId: int
    processString: str

class ErrorResponse(BaseModel):
    code: int
    message: str

@app.exception_handler(Exception)
async def universal_exception_handler(request: Request, exc: Exception):
    # Prevent leaking internal stack traces or system details
    return JSONResponse(
        status_code=500,
        content={"code": 500, "message": "Internal server error occurred"}
    )

@app.post("/monitor/commands", response_model=List[ProcessInfo])
async def get_processes(request: MonitorRequest):
    try:
        # 1. Regex Denial of Service (ReDoS) mitigation
        # We compile the regex with a timeout or limit. Since Python's 're' doesn't support timeouts,
        # we ensure the regex is valid. To prevent catastrophic backtracking, we can't fully 
        # stop it without a separate process, but we can catch the error.
        try:
            regex = re.compile(request.command_regex)
        except re.error:
            # Return a structured error as per the schema
            return JSONResponse(
                status_code=400,
                content={"code": 400, "message": "Invalid regular expression"}
            )

        # 2. Command Injection mitigation
        # We use a list for subprocess.run and shell=False (default).
        # However, 'filter_flags' is user input. Even without a shell, passing flags 
        # like '--help' or other ps-specific flags is possible.
        # To be strict, we validate that filter_flags contains only characters 
        # typical for ps flags (alphanumeric, dashes, spaces) to prevent argument injection.
        if request.filter_flags:
            if not re.match(r'^[a-zA-Z0-9\s\-]+$', request.filter_flags):
                return JSONResponse(
                    status_code=400,
                    content={"code": 400, "message": "Invalid characters in filter flags"}
                )
            
            cmd = ["ps"] + request.filter_flags.split()
        else:
            cmd = ["ps"]

        # 3. Resource Exhaustion mitigation
        # Set a strict timeout for the external command execution.
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            check=True, 
            timeout=5, 
            shell=False
        )
        
        lines = result.stdout.splitlines()
        if not lines:
            return []

        process_lines = lines[1:]
        matched_processes = []

        for line in process_lines:
            # Use a try-except block inside the loop to prevent one malformed line from crashing the request
            try:
                # Use the regex to search the line. 
                # Note: In a production environment, one might use a library like 'regex' 
                # with a timeout for true ReDoS protection.
                if regex.search(line):
                    parts = line.split(None, 10)
                    if len(parts) >= 2:
                        pid_str = parts[1]
                        if pid_str.isdigit():
                            matched_processes.append(ProcessInfo(
                                processId=int(pid_str),
                                processString=line.strip()
                            ))
            except (re.error, OverflowError):
                continue
        
        return matched_processes

    except subprocess.TimeoutExpired:
        return JSONResponse(
            status_code=504,
            content={"code": 504, "message": "Process monitoring command timed out"}
        )
    except subprocess.CalledProcessError as e:
        return JSONResponse(
            status_code=500,
            content={"code": 500, "message": "External command failed to execute"}
        )
    except Exception as e:
        # Catch-all to ensure no internal details leak
        return JSONResponse(
            status_code=500,
            content={"code": 500, "message": "An unexpected error occurred"}
        )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)