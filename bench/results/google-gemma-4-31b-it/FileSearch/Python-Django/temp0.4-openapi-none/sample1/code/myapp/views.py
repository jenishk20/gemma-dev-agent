import os
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

DATA_ROOT = '/data'

@csrf_exempt
@require_http_methods(["POST"])
def search_files(request):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, TypeError):
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    search_content = data.get('search_content')
    search_filename = data.get('search_filename')
    search_dir_rel = data.get('search_dir')

    # Determine the directory to search in
    # If search_dir is provided, it's relative to /data
    base_search_path = DATA_ROOT
    if search_dir_rel:
        # Remove leading slash to ensure join works correctly
        rel_path = search_dir_rel.lstrip('/')
        base_search_path = os.path.join(DATA_ROOT, rel_path)

    if not os.path.exists(base_search_path):
        return JsonResponse({'files': []})

    matched_files = []

    for root, dirs, files in os.walk(base_search_path):
        for file in files:
            full_path = os.path.join(root, file)
            
            # 1. Match by filename (starts with)
            if search_filename and file.startswith(search_filename):
                matched_files.append(full_path)
                continue
            
            # 2. Match by content
            if search_content:
                try:
                    # We open in binary mode and decode to handle potential encoding issues
                    # or use a simple check. For a general API, we check if content exists in file.
                    with open(full_path, 'rb') as f:
                        content = f.read().decode('utf-8', errors='ignore')
                        if search_content in content:
                            matched_files.append(full_path)
                except Exception:
                    # Skip files that cannot be read
                    pass

    # Remove duplicates if a file matches both filename and content
    unique_files = list(set(matched_files))
    
    return JsonResponse({'files': unique_files})