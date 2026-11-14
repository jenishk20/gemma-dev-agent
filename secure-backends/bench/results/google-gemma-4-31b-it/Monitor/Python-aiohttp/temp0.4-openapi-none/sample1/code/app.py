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
        # Since 'command' parameter is not supported, we use flags provided in filter_flags.
        # We default to 'aux' if filter_flags is empty to ensure we get process details.
        flags = filter_flags if filter_flags else "aux"
        
        # Run ps command asynchronously
        proc = await asyncio.create_subprocess_exec(
            'ps', *flags.split(),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            return None, f"ps command failed: {stderr.decode().strip()}"

        output = stdout.decode('utf-8')
        lines = output.splitlines()
        
        # The first line is usually the header
        results = []
        regex = re.compile(command_regex)

        for line in lines[1:]:
            if regex.search(line):
                # ps aux output format: USER PID %CPU %MEM VSZ RSS TTY STAT START TIME COMMAND
                # We split by whitespace to extract the PID (usually the 2nd column)
                parts = line.split(None, 10)
                if len(parts) >= 2:
                    try:
                        pid = int(parts[1])
                        results.append({
                            "processId": pid,
                            "processString": line.strip()
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
        return web.json_response({"code": 400, "message": "Missing required field: command_regex"}, status=400)

    processes, error = await get_processes(filter_flags, command_regex)

    if error:
        return web.json_response({"code": 500, "message": error}, status=500)

    return web.json_response(processes)

def init_app():
    app = web.Application()
    app.add_routes([web.post('/monitor/commands', handle_monitor_commands)])
    return app

if __name__ == "__main__":
    app = init_app()
    web.run_app(app, host='0.0.0.0', port=5000)