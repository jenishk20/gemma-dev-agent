import json
import re
import subprocess
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def monitor_commands(request):
    if request.method != 'POST':
        return JsonResponse({'code': 405, 'message': 'Method not allowed'}, status=405)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'code': 400, 'message': 'Invalid JSON'}, status=400)

    command_regex = data.get('command_regex')
    if not command_regex:
        return JsonResponse({'code': 400, 'message': 'command_regex is required'}, status=400)

    filter_flags = data.get('filter_flags', '')
    
    try:
        # Construct the ps command. 
        # We use 'ps' and pass the flags. 
        # We use shell=False for security, but since flags are passed as a string, 
        # we split them to provide a list to subprocess.
        cmd = ['ps']
        if filter_flags:
            cmd.extend(filter_flags.split())

        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        lines = result.stdout.strip().split('\n')
        
        # The first line is usually the header
        if len(lines) <= 1:
            return JsonResponse([], status=200)

        header = lines[0]
        process_lines = lines[1:]
        
        # We need to find which column is the PID. 
        # Standard 'ps aux' has PID as the second column.
        # However, we will assume a standard space-delimited output.
        # We will filter the full line against the regex.
        
        compiled_re = re.compile(command_regex)
        matching_processes = []

        for line in process_lines:
            if compiled_re.search(line):
                parts = line.split(None, 1) # Split into PID and the rest
                if len(parts) >= 2:
                    try:
                        pid = int(parts[0])
                        process_string = line.strip()
                        matching_processes.append({
                            'processId': pid,
                            'processString': process_string
                        })
                    except ValueError:
                        # If the first part isn't an integer, it's likely a header or malformed
                        continue

        return JsonResponse(matching_processes, safe=False, status=200)

    except Exception as e:
        return JsonResponse({'code': 500, 'message': str(e)}, status=500)