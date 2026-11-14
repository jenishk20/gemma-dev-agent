import json
import subprocess
import os
import tempfile
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

@csrf_exempt
@require_http_methods(["POST"])
def compile_code(request):
    try:
        data = json.loads(request.body)
        file_name = data.get('fileName')
        file_content = data.get('fileContent')
        
        if not file_name or not file_content:
            return JsonResponse({'error': 'Missing fileName or fileContent'}, status=400)

        # Create a temporary directory to avoid file collisions
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, file_name)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(file_content)

            if file_name.endswith('.ts'):
                # TypeScript compilation
                # -noEmit: just check for errors without generating JS
                # --esModuleInterop: common flag for compatibility
                cmd = ['tsc', file_path, '--noEmit', '--esModuleInterop']
            elif file_name.endswith('.cpp'):
                # C++ compilation
                cmd = ['g++', file_path, '-o', os.path.join(tmpdir, 'out')]
            else:
                return JsonResponse({'error': 'Unsupported file extension. Use .ts or .cpp'}, status=400)

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
                # Combine stdout and stderr as compilers use both
                error_msg = (process.stderr or process.stdout).strip()
                return JsonResponse({
                    'hasError': True,
                    'compilerError': error_msg if error_msg else "Unknown compilation error"
                })

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except subprocess.TimeoutExpired:
        return JsonResponse({'hasError': True, 'compilerError': 'Compilation timed out'}, status=200)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)