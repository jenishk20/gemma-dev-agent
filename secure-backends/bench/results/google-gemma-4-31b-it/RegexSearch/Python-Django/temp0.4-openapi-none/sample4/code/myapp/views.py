import os
import re
from django.http import JsonResponse
from django.conf import settings

def search_files(request):
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    regex_pattern = request.GET.get('regex')
    directory_rel = request.GET.get('directory', '')
    recursive = request.GET.get('recursive', 'false').lower() == 'true'

    if not regex_pattern:
        return JsonResponse({'error': 'Missing required parameter: regex'}, status=400)

    try:
        pattern = re.compile(regex_pattern)
    except re.error as e:
        return JsonResponse({'error': f'Invalid regex pattern: {str(e)}'}, status=400)

    # Root directory is ./files relative to server directory
    root_files_dir = os.path.join(settings.BASE_DIR, 'files')
    
    # Resolve target directory
    target_dir = os.path.join(root_files_dir, directory_rel)
    
    # Security check: ensure target_dir is within root_files_dir to prevent directory traversal
    normalized_root = os.path.abspath(root_files_dir)
    normalized_target = os.path.abspath(target_dir)
    if not normalized_target.startswith(normalized_root):
        return JsonResponse({'error': 'Directory path is outside of the allowed root'}, status=400)

    if not os.path.exists(target_dir) or not os.path.isdir(target_dir):
        return JsonResponse({'error': 'Specified directory does not exist or is not a directory'}, status=400)

    matching_files = []

    try:
        if recursive:
            for root, dirs, files in os.walk(target_dir):
                for file in files:
                    full_path = os.path.join(root, file)
                    try:
                        with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            if pattern.search(content):
                                # Calculate path relative to the search directory
                                rel_path = os.path.relpath(full_path, target_dir)
                                matching_files.append(rel_path)
                    except Exception:
                        continue
        else:
            for item in os.listdir(target_dir):
                full_path = os.path.join(target_dir, item)
                if os.path.isfile(full_path):
                    try:
                        with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            if pattern.search(content):
                                matching_files.append(item)
                    except Exception:
                        continue
    except Exception as e:
        return JsonResponse({'error': f'Internal server error: {str(e)}'}, status=500)

    return JsonResponse({'files': matching_files}, status=200)