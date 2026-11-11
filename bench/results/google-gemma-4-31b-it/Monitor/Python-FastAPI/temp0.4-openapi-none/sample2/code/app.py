import subprocess
import re
import uvicorn
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Monitor Service")

class MonitorRequest(BaseModel):
    filter_flags: Optional[str] = "aux"
    command_regex: str

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
        # We use the provided filter_flags. Default is 'aux'.
        # Since 'command' parameter is not supported, we rely on the flags provided.
        cmd = ["ps"]
        if request.filter_flags:
            # Split flags into list elements (e.g., "aux -T" -> ["aux", "-T"])
            cmd.extend(request.filter_flags.split())

        # Execute the ps command
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        output = result.stdout

        # Compile the regex for filtering
        regex = re.compile(request.command_regex)
        
        processes = []
        lines = output.splitlines()
        
        # Skip the header line of ps output
        for line in lines[1:]:
            if regex.search(line):
                # ps aux output typically starts with USER, PID, %CPU, %MEM, VSZ, RSS, TTY, STAT, START, TIME, COMMAND
                # We split by whitespace to extract the PID (usually the 2nd column)
                parts = line.split(None, 10)
                if len(parts) >= 2:
                    try:
                        pid = int(parts[1])
                        processes.append(ProcessInfo(processId=pid, processString=line))
                    except ValueError:
                        continue
        
        return processes

    except subprocess.CalledProcessError as e:
        raise HTTPException(
            status_code=500, 
            detail={"code": 500, "message": f"Command execution failed: {str(e)}"}
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail={"code": 500, "message": str(e)}
        )

if __name__ == "__main__":
    # Start the server on 0.0.0.0:5000
    uvicorn.run(app, host="0.0.0.0", port=5000)