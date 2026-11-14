import re
import subprocess
import shlex
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import uvicorn

app = FastAPI(title="Monitor Service", version="1.0.0")

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

def get_running_processes(flags: str, regex_pattern: str) -> List[ProcessInfo]:
    """
    Executes ps with provided flags and filters the output using a regex.
    """
    # Security: Validate flags to prevent command injection.
    # We only allow alphanumeric characters, spaces, and the '-' character.
    # This prevents passing shell operators like ';', '&', '|', etc.
    if not re.match(r'^[a-zA-Z0-9\s\-]+$', flags):
        raise ValueError("Invalid characters in filter_flags")

    try:
        # We use a list for subprocess.run to avoid shell=True, mitigating shell injection.
        # Since flags might contain multiple arguments (e.g., "aux -T"), we split them.
        cmd = ["ps"] + shlex.split(flags)
        
        # Capture output
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            check=True, 
            timeout=5
        )
        
        lines = result.stdout.splitlines()
        if not lines:
            return []

        # The first line is usually the header.
        header = lines[0]
        process_lines = lines[1:]
        
        # Compile the regex for efficiency and validation
        pattern = re.compile(regex_pattern)
        
        matches = []
        for line in process_lines:
            if pattern.search(line):
                # ps aux output typically starts with: USER PID %CPU %MEM VSZ RSS TTY STAT START TIME COMMAND
                # We split by whitespace to extract the PID (usually the 2nd column)
                parts = line.split(None, 1) 
                # Note: standard 'ps aux' format: USER PID ...
                # To be more robust across different 'ps' flag outputs, 
                # we split the line and try to find the first integer that looks like a PID.
                all_parts = line.split()
                pid = None
                for part in all_parts:
                    if part.isdigit():
                        pid = int(part)
                        break
                
                if pid is not None:
                    matches.append(ProcessInfo(processId=pid, processString=line.strip()))
        
        return matches

    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"ps command failed: {e.stderr}")
    except subprocess.TimeoutExpired:
        raise RuntimeError("ps command timed out")
    except Exception as e:
        raise RuntimeError(f"An unexpected error occurred: {str(e)}")

# --- Endpoints ---

@app.post(
    "/monitor/commands", 
    response_model=List[ProcessInfo], 
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}}
)
async def monitor_commands(request: MonitorRequest):
    """
    Returns the list of processes running on the server whose command string matches a given regular expression.
    """
    try:
        # Validate regex pattern to ensure it's valid
        re.compile(request.command_regex)
        
        processes = get_running_processes(request.filter_flags, request.command_regex)
        return processes
    except ValueError as ve:
        # This catches the flag validation error
        raise HTTPException(status_code=400, detail=ErrorResponse(code=400, message=str(ve)).model_dump())
    except re.error:
        # This catches invalid regex patterns
        raise HTTPException(status_code=400, detail=ErrorResponse(code=400, message="Invalid regular expression").model_dump())
    except RuntimeError as re_err:
        # This catches subprocess errors
        raise HTTPException(status_code=500, detail=ErrorResponse(code=500, message=str(re_err)).model_dump())
    except Exception as e:
        raise HTTPException(status_code=500, detail=ErrorResponse(code=500, message="Internal server error").model_dump())

if __name__ == "__main__":
    # Start the server on 0.0.0.0:5000
    uvicorn.run(app, host="0.0.0.0", port=5000)