import os
import re
from django.http import JsonResponse
from django.conf import settings

def search_files(request):
    regex_pattern = request.GET.get('regex')
    directory_rel = request.GET.get('directory', '')
    recursive_str = request.GET.get('recursive', 'false').lower()
    recursive = recursive_str == 'true'

    if not regex_pattern:
        return JsonResponse({'error': 'Missing required parameter: regex'}, status=400)

    try:
        pattern = re.compile(regex_pattern)
    except re.error as e:
        return JsonResponse({'error': f'Invalid regex pattern: {str(e)}'}, status=400)

    # Resolve the search path
    base_root = settings.FILES_ROOT
    search_path = base_root / directory_rel if directory_rel else base_root

    if not search_path.exists() or not search_path.is_dir():
        return JsonResponse({'error': 'Specified directory does not exist or is not accessible'}, status=400)

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
                                # Calculate path relative to the directory parameter
                                rel_path = os.path.relpath(full_path, search_path)
                                matching_files.append(rel_path)
                    except Exception:
                        continue
        else:
            for item in os.listdir(search_path):
                full_path = os.path.join(search_path, item)
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