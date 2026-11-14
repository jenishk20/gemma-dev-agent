import subprocess
import re
import uvicorn
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="Monitor Service", version="1.0.0")

# Request and Response Models based on OpenAPI schema
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
async def get_running_processes(request: MonitorRequest):
    """
    Returns the list of processes running on the server whose command string matches a given regular expression.
    """
    try:
        # Construct the ps command. 
        # Since 'command' parameter is not supported, we use flags provided in filter_flags.
        # We split filter_flags to pass them as individual arguments to subprocess.
        flags = request.filter_flags.split() if request.filter_flags else ["aux"]
        cmd = ["ps"] + flags

        # Execute ps command
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        output = result.stdout

        # Compile the regex for filtering
        pattern = re.compile(request.command_regex)
        
        processes = []
        # ps aux output usually has a header line, we skip it or let the regex handle it.
        lines = output.strip().split('\n')
        
        for line in lines:
            if pattern.search(line):
                # ps aux output format: USER PID %CPU %MEM VSZ RSS TTY STAT START TIME COMMAND
                # We split by whitespace to extract the PID (usually the 2nd column)
                parts = line.split(None, 10)
                if len(parts) >= 2:
                    try:
                        pid = int(parts[1])
                        # The process string is the full line as per common monitoring requirements
                        # or the command part. The schema asks for 'the complete string of the process'.
                        processes.append(ProcessInfo(processId=pid, processString=line))
                    except ValueError:
                        # Skip lines where the second column isn't an integer (like the header)
                        continue

        return processes

    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail={"code": 500, "message": f"ps command failed: {str(e)}"})
    except re.error as e:
        raise HTTPException(status_code=400, detail={"code": 400, "message": f"Invalid regular expression: {str(e)}"})
    except Exception as e:
        raise HTTPException(status_code=500, detail={"code": 500, "message": str(e)})

if __name__ == "__main__":
    # Start the server on 0.0.0.0:5000
    uvicorn.run(app, host="0.0.0.0", port=5000)