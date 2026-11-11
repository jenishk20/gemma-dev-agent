import os
import json
from django.http import FileResponse, HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt

SONGS_DIRECTORY = '/var/songs'

@csrf_exempt
def download_song(request):
    if request.method != 'POST':
        return HttpResponse(status=405)

    try:
        data = json.loads(request.body)
        filename = data.get('filename')
    except (json.JSONDecodeError, AttributeError):
        return HttpResponse(status=400)

    if not filename or not isinstance(filename, str):
        return HttpResponse(status=400)

    # Security check: prevent directory traversal attacks
    # Ensure the filename doesn't contain path separators
    if os.path.basename(filename) != filename:
        return HttpResponse(status=400)

    file_path = os.path.join(SONGS_DIRECTORY, filename)

    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        return HttpResponse(status=404)

    try:
        # FileResponse uses a streaming approach and is efficient for large files
        response = FileResponse(open(file_path, 'rb'), content_type='audio/mpeg')
        return response
    except Exception:
        return HttpResponse(status=500)