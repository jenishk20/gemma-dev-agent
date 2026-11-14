import os
import json
from django.http import HttpResponse, JsonResponse, FileResponse
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponseBadRequest

SONGS_DIRECTORY = '/var/songs'

@csrf_exempt
def download_song(request):
    if request.method != 'POST':
        return HttpResponse(status=405)

    try:
        data = json.loads(request.body)
        filename = data.get('filename')
    except json.JSONDecodeError:
        return HttpResponseBadRequest("Invalid JSON")

    if not filename or not isinstance(filename, str):
        return HttpResponseBadRequest("Invalid input: filename is required")

    # Security: Prevent directory traversal attacks
    # Normalize path and ensure it stays within SONGS_DIRECTORY
    safe_filename = os.path.basename(filename)
    file_path = os.path.join(SONGS_DIRECTORY, safe_filename)

    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        return HttpResponse(status=404)

    # Stream the file content
    # FileResponse is efficient for streaming large files
    response = FileResponse(open(file_path, 'rb'), content_type='audio/mpeg')
    return response