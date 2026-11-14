import re
import subprocess
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

# --- Implementation ---

@app.post("/monitor/commands", response_model=List[ProcessInfo])
async def get_running_processes(request: MonitorRequest):
    """
    Returns the list of processes running on the server whose command string matches a given regular expression.
    """
    try:
        # Security: Validate filter_flags to prevent command injection.
        # We only allow characters typically found in ps flags (letters, dashes, spaces).
        # This prevents the user from adding shell operators like ';', '&&', '|', etc.
        if request.filter_flags and not re.match(r'^[a-zA-Z\s\-]+$', request.filter_flags):
            raise HTTPException(status_code=400, detail="Invalid characters in filter_flags")

        # Construct the command. 
        # Since 'command' parameter is not supported, we use 'ps' with flags.
        # We use a list for subprocess.run to avoid shell=True vulnerabilities.
        # We split the flags string into a list.
        flags = shlex.split(request.filter_flags)
        cmd = ["ps"] + flags

        # Execute the process list command
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

        # The first line is usually the header
        header = lines[0]
        process_lines = lines[1:]

        # Compile the regex provided by the user
        try:
            pattern = re.compile(request.command_regex)
        except re.error:
            raise HTTPException(status_code=400, detail="Invalid regular expression")

        matching_processes = []

        for line in process_lines:
            # ps aux output typically starts with: USER PID %CPU %MEM VSZ RSS TTY STAT START TIME COMMAND
            # We split by whitespace to isolate the PID (usually the 2nd column)
            parts = line.split(None, 10) # Limit split to avoid breaking the command string
            if len(parts) < 11:
                continue
            
            pid_str = parts[1]
            command_str = parts[10]

            if pattern.search(command_str):
                try:
                    matching_processes.append(
                        ProcessInfo(processId=int(pid_str), processString=line.strip())
                    )
                except ValueError:
                    continue

        return matching_processes

    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"PS command failed: {str(e)}")
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Process retrieval timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

if __name__ == "__main__":
    # Start the server on 0.0.0.0:5000 as requested
    uvicorn.run(app, host="0.0.0.0", port=5000)