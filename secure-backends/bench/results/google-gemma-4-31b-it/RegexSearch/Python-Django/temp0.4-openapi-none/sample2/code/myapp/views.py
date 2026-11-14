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
        return JsonResponse({'error': f'Invalid regex: {str(e)}'}, status=400)

    root_dir = settings.FILES_ROOT
    search_path = os.path.join(root_dir, directory_rel)

    # Security check: ensure search_path is within root_dir
    abs_search_path = os.path.abspath(search_path)
    abs_root_dir = os.path.abspath(root_dir)
    if not abs_search_path.startswith(abs_root_dir):
        return JsonResponse({'error': 'Directory access denied'}, status=400)

    if not os.path.exists(search_path) or not os.path.isdir(search_path):
        return JsonResponse({'error': 'Directory not found or inaccessible'}, status=400)

    matching_files = []

    try:
        if recursive:
            for root, dirs, files in os.walk(search_path):
                for file in files:
                    full_path = os.path.join(root, file)
                    try:
                        with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            if pattern.search(content):
                                # Calculate path relative to the search directory
                                rel_path = os.path.relpath(full_path, search_path)
                                matching_files.append(rel_path)
                    except Exception:
                        continue
        else:
            for entry in os.scandir(search_path):
                if entry.is_file():
                    try:
                        with open(entry.path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            if pattern.search(content):
                                matching_files.append(entry.name)
                    except Exception:
                        continue
    except Exception as e:
        return JsonResponse({'error': f'Internal server error: {str(e)}'}, status=500)

    return JsonResponse({'files': matching_files}, status=200)