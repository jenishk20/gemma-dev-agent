import os
import subprocess
import json
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
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({'error': 'Invalid JSON body'}, status=400)

    if not file_name or not file_content:
        return JsonResponse({'error': 'Missing fileName or fileContent'}, status=400)

    # Create a temporary directory to avoid collisions and cleanup
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, file_name)
        with open(file_path, 'w') as f:
            f.write(file_content)

        has_error = False
        compiler_error = None

        if file_name.endswith('.cpp'):
            # C++ Compilation: g++ -fsyntax-only checks for compilation errors without producing binary
            cmd = ['g++', '-fsyntax-only', file_path]
            process = subprocess.run(cmd, capture_output=True, text=True)
            if process.returncode != 0:
                has_error = True
                compiler_error = process.stderr.strip()
        
        elif file_name.endswith('.ts'):
            # TypeScript Compilation: tsc
            # We need to create a basic tsconfig.json or use flags to ensure it compiles a single file
            cmd = ['tsc', file_path, '--noEmit', '--esModuleInterop', 'false']
            process = subprocess.run(cmd, capture_output=True, text=True)
            if process.returncode != 0:
                has_error = True
                compiler_error = process.stderr.strip() or process.stdout.strip()
        
        else:
            return JsonResponse({'error': 'Unsupported file extension. Use .cpp or .ts'}, status=400)

        return JsonResponse({
            'hasError': has_error,
            'compilerError': compiler_error
        })