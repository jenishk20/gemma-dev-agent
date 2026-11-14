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
        # Construct the command. 
        # Since 'command' parameter is not supported, we use flags like 'aux'
        # We split filter_flags to pass as a list to subprocess
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

        output = stdout.decode()
        lines = output.splitlines()
        
        # The first line is usually the header
        if not lines:
            return [], None
        
        header = lines[0]
        process_data = []
        
        # Compile regex for efficiency
        regex = re.compile(command_regex)

        for line in lines[1:]:
            # ps aux output format: USER PID %CPU %MEM VSZ RSS TTY STAT START TIME COMMAND
            # We split by whitespace. The command is usually the last part.
            parts = line.split(None, 10) 
            if len(parts) < 11:
                continue
            
            pid = parts[1]
            command_string = parts[10]

            if regex.search(command_string):
                try:
                    process_data.append({
                        "processId": int(pid),
                        "processString": command_string
                    })
                except ValueError:
                    continue
        
        return process_data, None

    except Exception as e:
        return None, str(e)

async def handle_monitor_commands(request):
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

async def init_app():
    app = web.Application()
    app.add_routes([web.post('/monitor/commands', handle_monitor_commands)])
    return app

if __name__ == "__main__":
    app = asyncio.run(init_app()) # This is a placeholder, we need the runner
    # Re-initializing for the actual runner
    app = web.Application()
    app.add_routes([web.post('/monitor/commands', handle_monitor_commands)])
    web.run_app(app, host='0.0.0.0', port=5000)