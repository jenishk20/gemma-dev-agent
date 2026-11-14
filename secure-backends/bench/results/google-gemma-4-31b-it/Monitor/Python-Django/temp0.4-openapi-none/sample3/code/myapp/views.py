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
    except (json.JSONDecodeError, TypeError):
        return JsonResponse({'code': 400, 'message': 'Invalid JSON body'}, status=400)

    command_regex = data.get('command_regex')
    if not command_regex:
        return JsonResponse({'code': 400, 'message': 'Missing required field: command_regex'}, status=400)

    filter_flags = data.get('filter_flags', '')
    
    try:
        # Construct the ps command. 
        # We use 'ps' and pass the provided flags. 
        # We must be careful to avoid shell injection, so we pass as a list.
        # Since filter_flags might contain multiple flags (e.g. "aux -T"), we split them.
        cmd = ['ps']
        if filter_flags:
            cmd.extend(filter_flags.split())
        
        # Execute ps command
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        output = result.stdout
        
        # The first line is usually the header
        lines = output.strip().split('\n')
        if not lines:
            return JsonResponse([], status=200)
            
        # We need to identify which column is the PID and which is the command.
        # Standard ps aux output: USER PID %CPU %MEM VSZ RSS TTY STAT START TIME COMMAND
        # Since the user can provide custom flags, we rely on a simple heuristic:
        # We search for lines matching the regex and try to extract the PID (usually the first integer).
        
        processes = []
        regex = re.compile(command_regex)
        
        # Skip header
        for line in lines[1:]:
            if regex.search(line):
                parts = line.split()
                if parts:
                    # Attempt to find the PID. In most 'ps' outputs, PID is the first or second column.
                    # We look for the first part that is purely numeric.
                    pid = None
                    for part in parts:
                        if part.isdigit():
                            pid = int(part)
                            break
                    
                    if pid is not None:
                        processes.append({
                            'processId': pid,
                            'processString': line.strip()
                        })
        
        return JsonResponse(processes, safe=False, status=200)

    except subprocess.CalledProcessError as e:
        return JsonResponse({'code': 500, 'message': f'Command execution failed: {str(e)}'}, status=500)
    except Exception as e:
        return JsonResponse({'code': 500, 'message': str(e)}, status=500)