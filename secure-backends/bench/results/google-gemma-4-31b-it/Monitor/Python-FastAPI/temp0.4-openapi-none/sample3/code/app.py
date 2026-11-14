import subprocess
import re
import uvicorn
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# --- Models ---

class MonitorRequest(BaseModel):
    filter_flags: Optional[str] = "aux"
    command_regex: str

class ProcessInfo(BaseModel):
    processId: int
    processString: str

class ErrorResponse(BaseModel):
    code: int
    message: str

# --- App Initialization ---

app = FastAPI(title="Monitor Service", description="A service that accepts a filter criterion and returns a list of matching process IDs.")

@app.post("/monitor/commands", response_model=List[ProcessInfo])
async def get_processes(request: MonitorRequest):
    """
    Returns the list of processes running on the server whose command string matches a given regular expression.
    """
    try:
        # Construct the ps command. 
        # Since 'command' parameter is not supported, we use flags provided in filter_flags.
        # We split filter_flags to avoid shell injection and pass as a list.
        flags = request.filter_flags.split()
        cmd = ["ps"] + flags
        
        # Execute ps command
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        output = result.stdout
        
        # Compile the regex for filtering
        regex = re.compile(request.command_regex)
        
        matching_processes = []
        
        # ps aux output usually has a header. We skip it and process lines.
        lines = output.strip().split('\n')
        if not lines:
            return []
            
        # The first line is usually the header (USER, PID, %CPU, etc.)
        # We iterate through the process lines.
        for line in lines[1:]:
            if regex.search(line):
                # Extract PID. In 'ps aux', PID is typically the second column.
                parts = line.split()
                if len(parts) > 1:
                    try:
                        pid = int(parts[1])
                        matching_processes.append(ProcessInfo(
                            processId=pid,
                            processString=line.strip()
                        ))
                    except ValueError:
                        # Skip lines where the second column isn't an integer
                        continue
        
        return matching_processes

    except subprocess.CalledProcessError as e:
        raise HTTPException(
            status_code=500, 
            detail={"code": 500, "message": f"Error executing ps command: {str(e)}"}
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail={"code": 500, "message": str(e)}
        )

if __name__ == "__main__":
    # Start the server on 0.0.0.0:5000
    uvicorn.run(app, host="0.0.0.0", port=5000)