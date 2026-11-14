import json
import os
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

LOG_FILE = os.path.join(settings.BASE_DIR, 'logs.txt')

@csrf_exempt
def log_handler(request):
    # Handle /log endpoint
    if request.path == '/log':
        if request.method == 'POST':
            try:
                data = json.loads(request.body)
                message = data.get('message', '')
                with open(LOG_FILE, 'a') as f:
                    f.write(message + '\n')
                return HttpResponse(status=200)
            except json.JSONDecodeError:
                return HttpResponse(status=400)
        return HttpResponse(status=405)

    # Handle /logs endpoint
    elif request.path == '/logs':
        if request.method == 'GET':
            if not os.path.exists(LOG_FILE):
                return HttpResponse("", content_type="text/plain")
            with open(LOG_FILE, 'r') as f:
                content = f.read()
            return HttpResponse(content, content_type="text/plain")
        return HttpResponse(status=405)

    return HttpResponse(status=404)