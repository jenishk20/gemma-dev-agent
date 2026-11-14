import json
import re
import subprocess
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
    filter_flags = data.get('filter_flags', 'aux')

    if not command_regex:
        return JsonResponse({'code': 400, 'message': 'command_regex is required'}, status=400)

    try:
        # Build the ps command. 
        # We split filter_flags to pass as a list to subprocess.
        cmd = ['ps'] + filter_flags.split()
        result = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True)
        
        lines = result.strip().split('\n')
        # The first line is usually the header
        process_list = []
        
        # Compile regex for performance and validation
        pattern = re.compile(command_regex)

        for line in lines[1:]:
            if not line.strip():
                continue
            
            # ps aux output: USER PID %CPU %MEM VSZ RSS TTY STAT START TIME COMMAND
            # We need PID (index 1) and the full command string (index 10 onwards)
            parts = line.split(None, 10)
            if len(parts) < 11:
                continue
                
            pid = parts[1]
            command_string = parts[10]

            if pattern.search(command_string):
                process_list.append({
                    'processId': int(pid),
                    'processString': line.strip()
                })

        return JsonResponse(process_list, safe=False)

    except Exception as e:
        return JsonResponse({'code': 500, 'message': str(e)}, status=500)