import subprocess
import re
import uvicorn
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

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

@app.post("/monitor/commands", response_model=List[ProcessInfo])
async def get_processes(request: MonitorRequest):
    try:
        # Construct the ps command. 
        # We use the provided filter_flags. We split them to pass as separate arguments to subprocess.
        flags = request.filter_flags.split()
        cmd = ["ps"] + flags
        
        # Execute ps command
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        output = result.stdout
        
        # Compile the regex for filtering
        pattern = re.compile(request.command_regex)
        
        processes = []
        lines = output.strip().split('\n')
        
        # The first line is usually the header
        if len(lines) <= 1:
            return []

        # ps aux output format: USER PID %CPU %MEM VSZ RSS TTY STAT START TIME COMMAND
        # We need to be careful about parsing since columns can vary.
        # We iterate through lines starting from the second one.
        for line in lines[1:]:
            if not line.strip():
                continue
            
            # Check if the line matches the regex
            if pattern.search(line):
                parts = line.split(None, 10) # Split into max 11 parts
                if len(parts) >= 2:
                    try:
                        pid = int(parts[1])
                        # The process string is the rest of the line after the PID and other metadata
                        # To be safe and match "complete string of the process", we take the whole line
                        processes.append(ProcessInfo(processId=pid, processString=line.strip()))
                    except ValueError:
                        continue
        
        return processes

    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=ErrorResponse(code=500, message=f"ps command failed: {str(e)}").model_dump())
    except Exception as e:
        raise HTTPException(status_code=500, detail=ErrorResponse(code=500, message=str(e)).model_dump())

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)