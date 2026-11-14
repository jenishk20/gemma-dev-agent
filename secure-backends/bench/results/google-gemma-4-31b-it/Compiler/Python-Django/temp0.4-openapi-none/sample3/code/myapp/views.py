import json
import subprocess
import tempfile
import os
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def compile_code(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        data = json.loads(request.body)
        file_name = data.get('fileName', '')
        file_content = data.get('file_content', data.get('fileContent', ''))
        
        if not file_name or not file_content:
            return JsonResponse({'error': 'Missing fileName or fileContent'}, status=400)

        # Use a temporary directory to avoid collisions and cleanup
        with tempfile.TemporaryDirectory() as tmpdir:
            full_path = os.path.join(tmpdir, file_name)
            with open(full_path, 'w') as f:
                f.write(file_content)

            if file_name.endswith('.ts'):
                # TypeScript compilation: tsc
                # We use --noEmit to just check for errors without generating JS files
                cmd = ['tsc', full_path, '--noEmit', '--esModuleInterop', '--target', 'es6']
            elif file_name.endswith('.cpp'):
                # C++ compilation: g++
                # -c compiles without linking
                cmd = ['g++', '-c', full_path]
            else:
                return JsonResponse({'error': 'Unsupported file extension'}, status=400)

            process = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=10
            )

            if process.returncode == 0:
                return JsonResponse({
                    'hasError': False,
                    'compilerError': None
                })
            else:
                # Return the stderr as the compiler error
                error_msg = process.stderr.strip() or process.stdout.strip()
                return JsonResponse({
                    'hasError': True,
                    'compilerError': error_msg
                })

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except subprocess.TimeoutExpired:
        return JsonResponse({'hasError': True, 'compilerError': 'Compilation timed out'}, status=200)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)