import subprocess
import re
import uvicorn
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

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

@app.post("/monitor/commands", response_model=List[ProcessInfo])
async def get_processes(request: MonitorRequest):
    try:
        # Construct the ps command. 
        # We use the provided filter_flags. Since 'command' param is not supported, 
        # we rely on the flags (like aux) to get the process list.
        cmd = ["ps"]
        if request.filter_flags:
            # Split flags into a list to avoid shell injection and handle spaces
            cmd.extend(request.filter_flags.split())
        
        # Execute the process list command
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        lines = result.stdout.splitlines()
        
        if not lines:
            return []

        # The first line is usually the header
        process_lines = lines[1:]
        
        matched_processes = []
        regex = re.compile(request.command_regex)

        for line in process_lines:
            # ps aux output typically starts with: USER PID %CPU %MEM VSZ RSS TTY STAT START TIME COMMAND
            # We need to extract the PID (usually the 2nd column) and the full string
            parts = line.split(None, 10) # Split into 11 parts max
            if len(parts) >= 2:
                pid_str = parts[1]
                # The 'command' part is the last element if we split by 10, 
                # but it's safer to just use the whole line for the regex match 
                # as the OpenAPI asks for the "complete string of the process"
                full_string = line.strip()
                
                if regex.search(full_string):
                    try:
                        matched_processes.append(ProcessInfo(
                            processId=int(pid_str),
                            processString=full_string
                        ))
                    except ValueError:
                        continue
        
        return matched_processes

    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"PS command failed: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)