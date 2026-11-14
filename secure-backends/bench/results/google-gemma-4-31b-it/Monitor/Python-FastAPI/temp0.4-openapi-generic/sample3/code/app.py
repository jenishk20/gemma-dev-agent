import subprocess
import re
import shlex
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import uvicorn

app = FastAPI(title="Monitor Service")

class MonitorRequest(BaseModel):
    filter_flags: Optional[str] = Field(
        default="aux", 
        description="Flags to filter and sort processes, matching the flags of the 'ps' command"
    )
    command_regex: str = Field(
        ..., 
        description="The regular expression of the commands to search for on the server"
    )

class ProcessInfo(BaseModel):
    processId: int
    processString: str

class ErrorResponse(BaseModel):
    code: int
    message: str

@app.post(
    "/monitor/commands", 
    response_model=List[ProcessInfo], 
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}}
)
async def get_running_processes(request: MonitorRequest):
    """
    Returns the list of processes running on the server whose command string matches a given regular expression.
    """
    try:
        # Security: Validate and sanitize filter_flags to prevent command injection.
        # We only allow characters typically found in ps flags (letters, dashes, spaces).
        # We use shlex.split to ensure the flags are treated as a list of arguments.
        sanitized_flags = re.sub(r'[^a-zA-Z0-9\s\-]', '', request.filter_flags)
        args = shlex.split(sanitized_flags)
        
        # Construct the command: ps [flags]
        # We avoid using shell=True to prevent shell injection.
        cmd = ["ps"] + args
        
        # Execute the process list command
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            check=True, 
            timeout=5
        )
        
        output = result.stdout
        lines = output.splitlines()
        
        # The first line is usually the header
        if not lines:
            return []
        
        # Compile the regex provided by the user
        try:
            pattern = re.compile(request.command_regex)
        except re.error as e:
            raise HTTPException(
                status_code=400, 
                detail={"code": 400, "message": f"Invalid regular expression: {str(e)}"}
            )

        matching_processes = []
        
        # Iterate through lines (skipping header)
        for line in lines[1:]:
            line = line.strip()
            if not line:
                continue
                
            if pattern.search(line):
                # ps aux output typically starts with USER, PID, %CPU, %MEM, VSZ, RSS, TTY, STAT, START, TIME, COMMAND
                # We split by whitespace to extract the PID (usually the 2nd column)
                parts = line.split(None, 10)
                if len(parts) >= 2:
                    try:
                        pid = int(parts[1])
                        matching_processes.append(ProcessInfo(
                            processId=pid,
                            processString=line
                        ))
                    except ValueError:
                        # Skip lines where the second column is not an integer
                        continue
        
        return matching_processes

    except subprocess.CalledProcessError as e:
        raise HTTPException(
            status_code=500, 
            detail={"code": 500, "message": f"Error executing ps command: {e.stderr}"}
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=500, 
            detail={"code": 500, "message": "The ps command timed out"}
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail={"code": 500, "message": str(e)}
        )

if __name__ == "__main__":
    # Start the server on 0.0.0.0:5000
    uvicorn.run(app, host="0.0.0.0", port=5000)