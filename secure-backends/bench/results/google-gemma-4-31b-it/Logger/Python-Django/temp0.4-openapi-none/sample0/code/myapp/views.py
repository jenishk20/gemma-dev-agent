import json
import os
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

LOG_FILE = "logs.txt"

@csrf_exempt
@require_http_methods(["POST"])
def log_message(request):
    try:
        data = json.loads(request.body)
        message = data.get("message", "")
        with open(LOG_FILE, "a") as f:
            f.write(message + "\n")
        return HttpResponse(status=200)
    except Exception:
        return HttpResponse(status=400)

@require_http_methods(["GET"])
def retrieve_logs(request):
    if not os.path.exists(LOG_FILE):
        return HttpResponse("", content_type="text/plain")
    
    with open(LOG_FILE, "r") as f:
        content = f.read()
    return HttpResponse(content, content_type="text/plain")