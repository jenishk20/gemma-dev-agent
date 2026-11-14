import asyncio
import re
import subprocess
from aiohttp import web

async def get_processes(filter_flags, command_regex):
    """
    Executes the ps command with provided flags and filters the output 
    based on the provided regular expression.
    """
    try:
        # Construct the command. Default to 'aux' if filter_flags is empty.
        # We split filter_flags to pass as a list to subprocess.
        flags = filter_flags.split() if filter_flags else ["aux"]
        cmd = ["ps"] + flags
        
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
        
        # The first line of 'ps aux' is usually the header
        if lines:
            lines = lines[1:]

        results = []
        regex = re.compile(command_regex)

        for line in lines:
            # ps aux output format: USER PID %CPU %MEM VSZ RSS TTY STAT START TIME COMMAND
            # We split by whitespace. PID is typically the second column.
            parts = line.split(None, 10)
            if len(parts) >= 11:
                pid = parts[1]
                command_string = parts[10]
                
                if regex.search(command_string):
                    try:
                        results.append({
                            "processId": int(pid),
                            "processString": command_string
                        })
                    except ValueError:
                        continue
        
        return results, None
    except Exception as e:
        return None, str(e)

async def handle_monitor_commands(request):
    """
    Handler for POST /monitor/commands
    """
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"code": 400, "message": "Invalid JSON body"}, status=400)

    command_regex = data.get("command_regex")
    filter_flags = data.get("filter_flags", "")

    if not command_regex:
        return web.json_response({"code": 400, "message": "command_regex is required"}, status=400)

    try:
        # Validate regex before using it
        re.compile(command_regex)
    except re.error:
        return web.json_response({"code": 400, "message": "Invalid regular expression"}, status=400)

    processes, error = await get_processes(filter_flags, command_regex)
    
    if error:
        return web.json_response({"code": 500, "message": error}, status=500)

    return web.json_response(processes, status=200)

app = web.Application()
app.add_routes([web.post('/monitor/commands', handle_monitor_commands)])

if __name__ == "__main__":
    web.run_app(app, port=5000, address="0.0.0.0")