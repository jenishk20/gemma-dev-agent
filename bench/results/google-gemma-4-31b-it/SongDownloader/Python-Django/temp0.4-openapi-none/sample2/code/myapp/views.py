import os
import json
from django.http import FileResponse, HttpResponseBadRequest, HttpResponseNotFound
from django.views.decorators.csrf import csrf_exempt

SONGS_DIRECTORY = '/var/songs'

@csrf_exempt
def download_song(request):
    if request.method != 'POST':
        return HttpResponseBadRequest("Only POST requests are allowed")

    try:
        data = json.loads(request.body)
        filename = data.get('filename')
    except (json.JSONDecodeError, AttributeError):
        return HttpResponseBadRequest("Invalid JSON input")

    if not filename or not isinstance(filename, str):
        return HttpResponseBadRequest("Missing or invalid filename")

    # Security: Prevent directory traversal attacks
    # Normalize path and ensure it's within the SONGS_DIRECTORY
    safe_filename = os.path.basename(filename)
    file_path = os.path.join(SONGS_DIRECTORY, safe_filename)

    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        return HttpResponseNotFound("File does not exist")

    # Stream the file content
    # FileResponse uses a streaming approach and automatically handles content-type
    # based on the file extension.
    response = FileResponse(open(file_path, 'rb'), content_type='audio/mpeg')
    return response