import os
import json
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.exceptions import SuspiciousOperation

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

    # Prevent directory traversal attacks
    # Ensure the filename does not contain path separators
    if os.path.basename(filename) != filename:
        return HttpResponse(status=400)

    file_path = os.path.join(SONGS_DIRECTORY, filename)

    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        return HttpResponse(status=404)

    try:
        with open(file_path, 'rb') as f:
            # For large files, we can use a streaming response, 
            # but for the sake of this API and standard Django HttpResponse:
            content = f.read()
            return HttpResponse(
                content, 
                content_type='audio/mpeg'
            )
    except Exception:
        return HttpResponse(status=500)