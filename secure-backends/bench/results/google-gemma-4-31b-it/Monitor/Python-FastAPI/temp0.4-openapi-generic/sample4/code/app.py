import re
import subprocess
import shlex
from typing import List, Optional
from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException
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

@app.post("/monitor/commands", response_model=List[ProcessInfo])
async def get_processes(request: MonitorRequest):
    """
    Returns the list of processes running on the server whose command string matches a given regular expression.
    """
    try:
        # Security: Validate filter_flags to prevent command injection.
        # We only allow characters common in ps flags (letters, dashes, spaces).
        # This prevents the user from adding shell operators like ';', '&', '|', etc.
        if request.filter_flags and not re.match(r'^[a-zA-Z\s\-]+$', request.filter_flags):
            raise HTTPException(status_code=400, detail="Invalid characters in filter_flags")

        # Build the command. We use a list with subprocess.run to avoid shell=True vulnerabilities.
        # Since 'ps' flags can be complex, we split the flags string into a list.
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
        
        output = result.stdout
        regex = re.compile(request.command_regex)
        
        processes = []
        lines = output.strip().split('\n')
        
        # The first line is usually the header
        if len(lines) <= 1:
            return []

        for line in lines[1:]:
            # We check if the line matches the regex
            if regex.search(line):
                # ps aux output typically starts with: USER PID %CPU %MEM VSZ RSS TTY STAT START TIME COMMAND
                # We split by whitespace to extract the PID (usually the second column)
                parts = line.split(None, 1)
                if len(parts) < 2:
                    continue
                
                # Further split the remaining part to isolate the PID
                # The first part was USER, the second part starts with PID
                remaining = parts[1].split(None, 1)
                if len(remaining) < 1:
                    continue
                
                try:
                    pid = int(remaining[0])
                    # The process string is the full line as per the schema requirement
                    processes.append(ProcessInfo(processId=pid, processString=line.strip()))
                except ValueError:
                    # If the second column isn't an integer, it's likely a header or malformed line
                    continue

        return processes

    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"PS command failed: {str(e)}")
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Process monitoring request timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

if __name__ == "__main__":
    # Start the server on 0.0.0.0:5000 as requested
    uvicorn.run(app, host="0.0.0.0", port=5000)