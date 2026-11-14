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

    base_data_dir = '/data'
    
    # Resolve the directory to search in
    if search_dir_rel:
        # Ensure the relative path is joined to /data and doesn't escape /data
        target_dir = os.path.normpath(os.path.join(base_data_dir, search_dir_rel.lstrip('/')))
    else:
        target_dir = base_data_dir

    if not target_dir.startswith(base_data_dir):
        return JsonResponse({'error': 'Invalid search directory'}, status=400)

    if not os.path.exists(target_dir) or not os.path.isdir(target_dir):
        return JsonResponse({'files': []})

    matched_files = []

    for root, dirs, files in os.walk(target_dir):
        for file in files:
            full_path = os.path.join(root, file)
            
            # Filter by filename if specified
            if search_filename and not file.startswith(search_filename):
                continue
            
            # Filter by content if specified
            if search_content:
                try:
                    with open(full_path, 'r', errors='ignore') as f:
                        if search_content not in f.read():
                            continue
                except Exception:
                    continue
            
            matched_files.append(full_path)

    return JsonResponse({'files': matched_files}, status=200)