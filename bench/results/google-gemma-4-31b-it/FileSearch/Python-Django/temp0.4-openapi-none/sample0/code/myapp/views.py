import os
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def search_files(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    search_content = data.get('search_content')
    search_filename = data.get('search_filename')
    search_dir_rel = data.get('search_dir')

    # Base directory is /data
    base_data_dir = '/data'
    
    # Resolve the search directory
    # If search_dir is provided, it's relative to /data
    target_dir = base_data_dir
    if search_dir_rel:
        # Remove leading slash if present to join correctly
        rel_path = search_dir_rel.lstrip('/')
        target_dir = os.path.join(base_data_dir, rel_path)

    if not os.path.exists(target_dir) or not os.path.isdir(target_dir):
        return JsonResponse({'files': []}, status=200)

    matched_files = []

    # Walk through the directory
    for root, dirs, files in os.walk(target_dir):
        for file in files:
            full_path = os.path.join(root, file)
            
            # Check filename match (starts with or matches)
            name_match = False
            if search_filename and file.startswith(search_filename):
                name_match = True
            
            # Check content match
            content_match = False
            if search_content:
                try:
                    # We open in binary mode and check for bytes to avoid encoding crashes
                    # with non-text files
                    with open(full_path, 'rb') as f:
                        if search_content.encode('utf-8') in f.read():
                            content_match = True
                except (OSError, IOError):
                    pass # Skip files that cannot be read

            # If either condition is met (or if both are null, we don't match)
            # The schema implies we search for content OR filename.
            # If both are null, we return nothing.
            if (search_filename or search_content) and (name_match or content_match):
                matched_files.append(full_path)

    return JsonResponse({'files': matched_files}, status=200)