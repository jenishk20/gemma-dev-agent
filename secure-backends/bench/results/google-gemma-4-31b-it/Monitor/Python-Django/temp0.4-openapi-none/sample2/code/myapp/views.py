import subprocess
import re
import json
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
        # Use ps with provided flags. 
        # Since 'command' parameter is not supported, we use the flags provided in filter_flags.
        # We split filter_flags to pass as separate arguments to subprocess.
        args = ['ps'] + filter_flags.split()
        result = subprocess.check_output(args, stderr=subprocess.STDOUT, text=True)
        
        lines = result.strip().split('\n')
        # Remove header line
        if len(lines) > 1:
            lines = lines[1:]
        else:
            lines = []

        pattern = re.compile(command_regex)
        matching_processes = []

        for line in lines:
            if pattern.search(line):
                # ps aux output usually starts with user, then pid.
                # We split by whitespace to extract the PID (usually the second column)
                parts = line.split()
                if len(parts) >= 2:
                    try:
                        pid = int(parts[1])
                        matching_processes.append({
                            'processId': pid,
                            'processString': line.strip()
                        })
                    except ValueError:
                        continue

        return JsonResponse(matching_processes, safe=False, status=200)

    except subprocess.CalledProcessError as e:
        return JsonResponse({'code': 500, 'message': f'ps command failed: {str(e)}'}, status=500)
    except Exception as e:
        return JsonResponse({'code': 500, 'message': str(e)}, status=500)