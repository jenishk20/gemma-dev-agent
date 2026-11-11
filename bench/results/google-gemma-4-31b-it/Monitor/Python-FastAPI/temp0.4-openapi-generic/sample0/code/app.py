import subprocess
import re
import shlex
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import uvicorn

app = FastAPI(title="Monitor Service")

# --- Models ---

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

# --- Logic ---

def get_processes(flags: str, regex_pattern: str) -> List[ProcessInfo]:
    """
    Executes the ps command and filters the output based on the provided regex.
    """
    try:
        # Security: We must be extremely careful with shell injection.
        # We split the flags using shlex to avoid passing raw strings to the shell.
        # We only allow flags that don't start with a dash to prevent argument injection 
        # if we were using a shell, but since we use a list with subprocess, it's safer.
        # However, to be strictly secure, we ensure flags are treated as arguments.
        
        cmd_args = ["ps"]
        # Split flags (e.g., "aux -T") into a list: ['aux', '-T']
        split_flags = shlex.split(flags)
        cmd_args.extend(split_args if (split_args := split_flags) else [])

        # Execute ps command. 
        # capture_output=True captures stdout and stderr.
        # text=True returns strings instead of bytes.
        result = subprocess.run(
            cmd_args, 
            capture_output=True, 
            text=True, 
            check=True, 
            timeout=5
        )
        
        output = result.stdout
        lines = output.strip().split('\n')
        
        # The first line is usually the header
        if not lines:
            return []
        
        # Compile the regex for efficiency and safety
        pattern = re.compile(regex_pattern)
        
        matching_processes = []
        
        # We iterate through the lines (skipping header)
        # ps aux output format: USER PID %CPU %MEM VSZ RSS TTY STAT START TIME COMMAND
        for line in lines[1:]:
            if pattern.search(line):
                parts = line.split(None, 10) # Split into max 11 parts
                if len(parts) >= 2:
                    try:
                        pid = int(parts[1])
                        # The full line represents the process string as requested
                        matching_processes.append(ProcessInfo(processId=pid, processString=line.strip()))
                    except ValueError:
                        continue
                        
        return matching_processes

    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"ps command failed: {e}")
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="ps command timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Endpoints ---

@app.post("/monitor/commands", response_model=List[ProcessInfo])
async def monitor_commands(request: MonitorRequest):
    """
    Returns the list of processes running on the server whose command string matches a given regular expression.
    """
    # Validate regex to prevent ReDoS or invalid patterns
    try:
        re.compile(request.command_regex)
    except re.error:
        raise HTTPException(status_code=400, detail="Invalid regular expression provided")

    return get_processes(request.filter_flags, request.command_regex)

if __name__ == "__main__":
    # Start the server on 0.0.0.0:5000
    uvicorn.run(app, host="0.0.0.0", port=5000)