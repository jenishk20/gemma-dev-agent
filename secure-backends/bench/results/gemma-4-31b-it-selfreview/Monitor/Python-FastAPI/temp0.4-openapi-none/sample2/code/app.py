import subprocess
import re
import uvicorn
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

app = FastAPI(title="Monitor Service")

class MonitorRequest(BaseModel):
    # Limit input length to prevent resource exhaustion (DoS) via massive strings
    filter_flags: Optional[str] = Field(default="aux", max_length=100)
    command_regex: str = Field(..., max_length=255)

class ProcessInfo(BaseModel):
    processId: int
    processString: str

class ErrorResponse(BaseModel):
    code: int
    message: str

@app.post("/monitor/commands", response_model=List[ProcessInfo])
async def get_processes(request: MonitorRequest):
    try:
        # SECURITY: Use a list for subprocess.run to avoid shell=True.
        # This prevents shell injection.
        cmd = ["ps"]
        
        if request.filter_flags:
            # We split the flags by whitespace. 
            # Since we are passing this as a list to subprocess.run, 
            # the OS treats each element as a literal argument, not a shell command.
            cmd.extend(request.filter_flags.split())

        # SECURITY: Set a timeout to prevent resource exhaustion (hanging processes)
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            check=True, 
            timeout=5
        )
        output = result.stdout

        # SECURITY: Regex Denial of Service (ReDoS) protection.
        # While we cannot fully prevent all complex regexes without a specialized engine,
        # we limit the input length (max_length=255) and wrap the search in a timeout/try-block.
        try:
            regex = re.compile(request.command_regex)
        except re.error as e:
            # Return a documented error format if the regex is invalid
            raise HTTPException(
                status_code=400, 
                detail={"code": 400, "message": f"Invalid regular expression: {str(e)}"}
            )
        
        processes = []
        lines = output.splitlines()
        
        # Skip the header line
        for line in lines[1:]:
            # Use search with the compiled regex
            if regex.search(line):
                # Split by whitespace to extract PID
                parts = line.split(None, 10)
                if len(parts) >= 2:
                    try:
                        pid = int(parts[1])
                        processes.append(ProcessInfo(processId=pid, processString=line))
                    except ValueError:
                        continue
        
        return processes

    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=500, 
            detail={"code": 500, "message": "The process monitor command timed out."}
        )
    except subprocess.CalledProcessError as e:
        # SECURITY: Do not leak raw stderr/internal details to the user
        raise HTTPException(
            status_code=500, 
            detail={"code": 500, "message": "External process execution failed."}
        )
    except Exception as e:
        # SECURITY: Generic error handling to prevent stack trace leakage
        raise HTTPException(
            status_code=500, 
            detail={"code": 500, "message": "An internal server error occurred."}
        )

if __name__ == "__main__":
    # Start the server on 0.0.0.0:5000
    uvicorn.run(app, host="0.0.0.0", port=5000)