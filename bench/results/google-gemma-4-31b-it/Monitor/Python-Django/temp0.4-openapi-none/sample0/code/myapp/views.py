import json
import subprocess
import re
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def monitor_commands(request):
    if request.method != 'POST':
        return JsonResponse({'code': 405, 'message': 'Method Not Allowed'}, status=405)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'code': 400, 'message': 'Invalid JSON'}, status=400)

    command_regex = data.get('command_regex')
    filter_flags = data.get('filter_flags', '')

    if not command_regex:
        return JsonResponse({'code': 400, 'message': 'command_regex is required'}, status=400)

    try:
        # Construct the ps command. 
        # We use 'ps' and append the filter_flags provided by the user.
        # Since the prompt mentions "command" parameter is not supported, 
        # we rely on the flags provided in filter_flags (e.g., "aux").
        cmd = ['ps']
        if filter_flags:
            cmd.extend(filter_flags.split())

        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        output = result.stdout

        # Compile the regex for filtering
        pattern = re.compile(command_regex)
        
        processes = []
        lines = output.splitlines()
        
        # Skip the header line of ps output
        for line in lines[1:]:
            if pattern.search(line):
                # ps aux output usually starts with USER, PID, %CPU, %MEM, VSZ, RSS, TTY, STAT, START, TIME, COMMAND
                # We split by whitespace to extract the PID (usually the second column)
                parts = line.split()
                if len(parts) >= 2:
                    try:
                        pid = int(parts[1])
                        processes.append({
                            'processId': pid,
                            'processString': line
                        })
                    except ValueError:
                        continue
        
        return JsonResponse(processes, safe=False, status=200)

    except subprocess.CalledProcessError as e:
        return JsonResponse({'code': 500, 'message': f'PS command failed: {str(e)}'}, status=500)
    except Exception as e:
        return JsonResponse({'code': 500, 'message': str(e)}, status=500)