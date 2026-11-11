import asyncio
import re
import subprocess
from aiohttp import web

async def get_processes(filter_flags, command_regex):
    """
    Executes the ps command and filters the output based on the provided regex.
    """
    try:
        # Construct the ps command. 
        # Since 'command' parameter is not supported, we use the flags provided (e.g., aux).
        # We split filter_flags to pass as a list to subprocess.
        cmd = ["ps"] + filter_flags.split()
        
        # Run the process asynchronously
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            return None, f"ps command failed: {stderr.decode().strip()}"

        output = stdout.decode('utf-8')
        lines = output.splitlines()
        
        # The first line is usually the header
        if not lines:
            return [], None
        
        header = lines[0]
        data_lines = lines[1:]
        
        results = []
        regex = re.compile(command_regex)
        
        for line in data_lines:
            # ps aux output typically starts with USER, PID, %CPU, %MEM, VSZ, RSS, TTY, STAT, START, TIME, COMMAND
            # We split by whitespace to extract the PID (usually the 2nd column)
            parts = line.split(None, 10)
            if len(parts) < 2:
                continue
                
            pid_str = parts[1]
            # The rest of the line is the process info/command
            process_string = " ".join(parts[1:])
            
            if regex.search(process_string):
                try:
                    results.append({
                        "processId": int(pid_str),
                        "processString": process_string
                    })
                except ValueError:
                    continue
        
        return results, None
    except Exception as e:
        return None, str(e)

async def handle_monitor_commands(request):
    """
    POST handler for /monitor/commands
    """
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"code": 400, "message": "Invalid JSON body"}, status=400)

    command_regex = data.get("command_regex")
    filter_flags = data.get("filter_flags", "aux")

    if not command_regex:
        return web.json_response({"code": 400, "message": "Missing required field: command_regex"}, status=400)

    processes, error = await get_processes(filter_flags, command_regex)
    
    if error:
        return web.json_response({"code": 500, "message": error}, status=500)

    return web.json_response(processes)

def main():
    app = web.Application()
    app.add_routes([web.post('/monitor/commands', handle_monitor_commands)])
    
    print("Starting server on 0.0.0.0:5000...")
    web.run_app(app, host='0.0.0.0', port=5000)

if __name__ == "__main__":
    main()