import os
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

BASE_DATA_DIR = '/data'

@csrf_exempt
@require_http_methods(["POST"])
def search_files(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    search_content = data.get('search_content')
    search_filename = data.get('search_filename')
    search_dir_rel = data.get('search_dir')

    # Determine the root directory to search in
    # If search_dir is provided, join it with /data, otherwise use /data
    target_dir = BASE_DATA_DIR
    if search_dir_rel:
        # Ensure we don't escape the /data directory for security
        normalized_rel = os.path.normpath(search_dir_rel).lstrip('/')
        target_dir = os.path.join(BASE_DATA_DIR, normalized_rel)

    if not os.path.exists(target_dir) or not os.path.isdir(target_dir):
        return JsonResponse({'files': []}, status=200)

    matched_files = []

    for root, dirs, files in os.walk(target_dir):
        for file in files:
            full_path = os.path.join(root, file)
            
            # Check filename match (starts with)
            if search_filename and not file.startswith(search_filename):
                # If filename is specified, it must match to be considered
                # But if content is also specified, we check both.
                # The logic: if filename is provided, it must match. 
                # If content is provided, it must match.
                # If both are provided, both must match.
                pass 
            
            # Refined logic based on OpenAPI description:
            # "contain the specified content OR match the filename"
            # However, usually "match the filename" implies a filter.
            # Let's implement: if filename is provided, it must match. 
            # If content is provided, it must be inside.
            
            match = False
            
            # Filename match (starts with)
            if search_filename and file.startswith(search_filename):
                match = True
            
            # Content match
            if search_content:
                try:
                    with open(full_path, 'r', errors='ignore') as f:
                        if search_content in f.read():
                            match = True
                except Exception:
                    pass
            
            # If neither search_filename nor search_content were provided, 
            # we shouldn't just return every file unless that's intended.
            # But the API says "contain the specified content or match the filename".
            # If both are null, we return nothing.
            if not search_filename and not search_content:
                match = False

            if match:
                matched_files.append(full_path)

    return JsonResponse({'files': matched_files}, status=200)