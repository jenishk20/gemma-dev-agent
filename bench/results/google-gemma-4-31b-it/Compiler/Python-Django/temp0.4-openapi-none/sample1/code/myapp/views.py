import json
import subprocess
import os
import tempfile
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def compile_code(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        data = json.loads(request.body)
        file_name = data.get('fileName', 'main.cpp')
        file_content = data.get('fileContent', '')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    if not file_name or not file_content:
        return JsonResponse({'error': 'Missing fileName or fileContent'}, status=400)

    # Use a temporary directory to avoid collisions and security issues
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, file_name)
        with open(file_path, 'w') as f:
            f.write(file_content)

        has_error = False
        compiler_error = None

        if file_name.endswith('.ts'):
            # TypeScript compilation
            # -noEmit ensures we only check for errors without creating JS files
            try:
                result = subprocess.run(
                    ['tsc', file_path, '--noEmit', '--esModuleInterop', '--target', 'es5'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode != 0:
                    has_error = True
                    compiler_error = result.stdout.strip() or result.stderr.strip()
            except Exception as e:
                has_error = True
                compiler_error = str(e)

        elif file_name.endswith('.cpp'):
            # C++ compilation
            try:
                result = subprocess.run(
                    ['g++', file_path, '-o', os.path.join(tmpdir, 'out')],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode != 0:
                    has_error = True
                    compiler_error = result.stderr.strip()
            except Exception as e:
                has_error = True
                compiler_error = str(e)
        else:
            return JsonResponse({'error': 'Unsupported file extension. Use .ts or .cpp'}, status=400)

        return JsonResponse({
            'hasError': has_error,
            'compilerError': compiler_error
        })