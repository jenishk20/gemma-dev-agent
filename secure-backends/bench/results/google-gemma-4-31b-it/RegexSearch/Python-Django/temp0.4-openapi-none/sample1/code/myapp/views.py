import os
import re
from django.http import JsonResponse
from django.conf import settings
from django.views import View

class SearchFilesView(View):
    def get(self, request):
        regex_pattern = request.GET.get('regex')
        directory_rel = request.GET.get('directory', '')
        recursive_str = request.GET.get('recursive', 'false').lower()
        recursive = recursive_str == 'true'

        if not regex_pattern:
            return JsonResponse({'error': 'regex parameter is required'}, status=400)

        try:
            pattern = re.compile(regex_pattern)
        except re.error as e:
            return JsonResponse({'error': f'Invalid regex: {str(e)}'}, status=400)

        # Resolve root directory
        root_dir = settings.FILES_ROOT
        search_dir = root_dir / directory_rel if hasattr(root_dir, 'joinpath') else os.path.join(root_dir, directory_rel)
        
        # Use Pathlib for cleaner path handling
        from pathlib import Path
        base_path = Path(settings.FILES_ROOT)
        target_path = base_path / directory_rel

        if not target_path.exists() or not target_path.is_dir():
            return JsonResponse({'error': 'Directory not found or inaccessible'}, status=400)

        matching_files = []

        try:
            if recursive:
                # rglob matches files recursively
                for path in target_path.rglob('*'):
                    if path.is_file():
                        if self.check_file_content(path, pattern):
                            # Return path relative to the search directory as per schema
                            matching_files.append(str(path.relative_to(target_path)))
            else:
                # glob matches files in current directory only
                for path in target_path.glob('*'):
                    if path.is_file():
                        if self.check_file_content(path, pattern):
                            matching_files.append(path.name)
        except Exception as e:
            return JsonResponse({'error': f'Internal server error: {str(e)}'}, status=500)

        return JsonResponse({'files': matching_files}, status=200)

    def check_file_content(self, path, pattern):
        try:
            # Read as bytes and decode to handle potential encoding issues gracefully
            with open(path, 'rb') as f:
                content = f.read().decode('utf-8', errors='ignore')
                return bool(pattern.search(content))
        except Exception:
            return False