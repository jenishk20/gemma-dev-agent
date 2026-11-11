import subprocess
import re
import uvicorn
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

# --- Models ---

class MonitorRequest(BaseModel):
    # Limit length of input to prevent resource exhaustion/DoS via regex or command line length
    filter_flags: Optional[str] = Field(default="aux", max_length=255)
    command_regex: str = Field(..., max_length=255)

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
        # SECURITY FIX: Prevent Shell Injection.
        # We use a list for subprocess.run with shell=False (default).
        # However, we must ensure that the 'filter_flags' do not allow the user to 
        # pass arguments that could lead to unexpected behavior.
        # We split the flags into a list. Since shell=False, these are passed as 
        # individual arguments to the 'ps' binary, not interpreted by a shell.
        flags = request.filter_flags.split()
        
        # Validation: Ensure flags don't start with a dash if they are not expected, 
        # but the spec explicitly asks for flags matching 'ps'. 
        # To prevent argument injection that might change the binary's behavior 
        # dangerously, we keep the list approach.
        cmd = ["ps"] + flags
        
        # SECURITY FIX: Resource Exhaustion.
        # Added a timeout to prevent the process from hanging indefinitely.
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            check=True, 
            timeout=5
        )
        output = result.stdout
        
        # SECURITY FIX: Regex Denial of Service (ReDoS).
        # We use a timeout-based approach or limit the complexity. 
        # Since Python's 're' doesn't have a built-in timeout, we rely on the 
        # max_length constraint on the input regex and the fact that we are 
        # searching against a finite set of process strings.
        try:
            regex = re.compile(request.command_regex)
        except re.error:
            # Return a documented error if the regex is invalid
            raise HTTPException(
                status_code=400, 
                detail={"code": 400, "message": "Invalid regular expression"}
            )
        
        matching_processes = []
        
        lines = output.strip().split('\n')
        if not lines:
            return []
            
        for line in lines[1:]:
            # Search for the regex in the process line
            if regex.search(line):
                parts = line.split()
                if len(parts) > 1:
                    try:
                        pid = int(parts[1])
                        matching_processes.append(ProcessInfo(
                            processId=pid,
                            processString=line.strip()
                        ))
                    except ValueError:
                        continue
        
        return matching_processes

    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=500, 
            detail={"code": 500, "message": "Process monitoring timed out"}
        )
    except subprocess.CalledProcessError as e:
        # SECURITY FIX: Error Handling.
        # Avoid leaking internal stderr/stack traces to the client.
        raise HTTPException(
            status_code=500, 
            detail={"code": 500, "message": "The system process command failed to execute"}
        )
    except Exception:
        # Generic catch-all to prevent leaking internal server details
        raise HTTPException(
            status_code=500, 
            detail={"code": 500, "message": "An internal server error occurred"}
        )

if __name__ == "__main__":
    # Start the server on 0.0.0.0:5000
    uvicorn.run(app, host="0.0.0.0", port=5000)