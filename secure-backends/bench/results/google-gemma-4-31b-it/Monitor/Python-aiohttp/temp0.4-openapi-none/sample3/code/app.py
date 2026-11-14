import asyncio
import re
import subprocess
from aiohttp import web

async def get_processes(filter_flags, command_regex):
    """
    Executes the ps command and filters the output based on the provided regex.
    """
    try:
        # Use the provided filter_flags (e.g., 'aux -T')
        # We split the flags to pass them as a list to subprocess
        cmd = ['ps'] + filter_flags.split()
        
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
        
        # Compile the regex for filtering
        pattern = re.compile(command_regex)
        
        results = []
        # We skip the header line (lines[0])
        for line in lines[1:]:
            if pattern.search(line):
                # ps aux typically starts with: USER PID %CPU %MEM VSZ RSS TTY STAT START TIME COMMAND
                # We split by whitespace and take the second element as PID
                parts = line.split(None, 10) # Split up to 10 times to keep the command string intact
                if len(parts) >= 2:
                    try:
                        pid = int(parts[1])
                        # The process string is the full line as per the OpenAPI description
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
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"code": 400, "message": "Invalid JSON body"}, status=400)

    command_regex = data.get('command_regex')
    filter_flags = data.get('filter_flags', 'aux')

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

if __name__ == '__main__':
    app = asyncio.run(init_app())
    web.run_app(app, host='0.0.0.0', port=5000)