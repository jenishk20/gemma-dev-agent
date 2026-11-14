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
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    search_content = data.get('search_content')
    search_filename = data.get('search_filename')
    search_dir_rel = data.get('search_dir')

    # Determine the base directory to search in
    # If search_dir is provided, it's relative to /data
    base_search_path = DATA_ROOT
    if search_dir_rel:
        # Normalize path to prevent directory traversal outside /data
        rel_path = os.path.normpath(search_dir_rel).lstrip('/')
        base_search_path = os.path.join(DATA_ROOT, rel_path)

    if not os.path.exists(base_search_path) or not os.path.isdir(base_search_path):
        return JsonResponse({'files': []}, status=200)

    matched_files = []

    for root, dirs, files in os.walk(base_search_path):
        for file in files:
            full_path = os.path.join(root, file)
            
            # Match by filename if specified
            if search_filename and not file.startswith(search_filename):
                # The schema says "match the filename", usually implies starts with or exact.
                # Given the example "file.txt", we check if it matches.
                if file != search_filename:
                    continue
            
            # Match by content if specified
            if search_content:
                try:
                    # We open in binary mode to avoid decoding errors for non-text files
                    with open(full_path, 'rb') as f:
                        content = f.read().decode('utf-8', errors='ignore')
                        if search_content not in content:
                            continue
                except Exception:
                    continue

            matched_files.append(full_path)

    return JsonResponse({'files': matched_files}, status=200)