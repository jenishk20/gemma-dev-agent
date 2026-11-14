import os
import json
from django.http import HttpResponse, JsonResponse, FileResponse
from django.views.decorators.csrf import csrf_exempt

SONGS_DIRECTORY = '/var/songs'

@csrf_exempt
def download_song(request):
    if request.method != 'POST':
        return HttpResponse(status=405)

    try:
        data = json.loads(request.body)
        filename = data.get('filename')
    except (json.JSONDecodeError, UnicodeDecodeError):
        return HttpResponse(status=400)

    if not filename or not isinstance(filename, str):
        return HttpResponse(status=400)

    # Security: Prevent directory traversal attacks
    # Ensure the filename is just a name and doesn't contain path separators
    safe_filename = os.path.basename(filename)
    if safe_filename != filename:
        return HttpResponse(status=400)

    file_path = os.path.join(SONGS_DIRECTORY, safe_filename)

    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        return HttpResponse(status=404)

    # Stream the file as audio/mpeg as per OpenAPI spec
    return FileResponse(open(file_path, 'rb'), content_type='audio/mpeg')