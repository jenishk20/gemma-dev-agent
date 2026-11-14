import json
import subprocess
import tempfile
import os
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

@csrf_exempt
@require_http_methods(["POST"])
def compile_code(request):
    try:
        data = json.loads(request.body)
        file_name = data.get('fileName', '')
        file_content = data.get('fileContent', '')
        
        if not file_name or not file_content:
            return JsonResponse({'error': 'Missing fileName or fileContent'}, status=400)

        # Create a temporary directory to avoid file collisions
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, file_name)
            with open(file_path, 'w') as f:
                f.write(file_content)

            if file_name.endswith('.ts'):
                # TypeScript compilation using tsc
                # --noEmit ensures we just check for errors without writing .js files
                process = subprocess.run(
                    ['tsc', file_path, '--noEmit', '--noEmitOnError'],
                    capture_output=True,
                    text=True
                )
            elif file_name.endswith('.cpp'):
                # C++ compilation using g++
                process = subprocess.run(
                    ['g++', file_path, '-o', os.path.join(tmpdir, 'out')],
                    capture_output=True,
                    text=True
                )
            else:
                return JsonResponse({'error': 'Unsupported file extension. Use .ts or .cpp'}, status=400)

            if process.returncode != 0:
                # Combine stderr and stdout as different compilers report errors in different streams
                error_msg = process.stderr.strip() or process.stdout.strip()
                return JsonResponse({
                    'hasError': True,
                    'compilerError': error_msg
                }, status=200)
            else:
                return JsonResponse({
                    'hasError': False,
                    'compilerError': None
                }, status=200)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)