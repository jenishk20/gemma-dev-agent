import json
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

LOG_FILE = "logs.txt"

@csrf_exempt
@require_http_methods(["POST"])
def log_message(request):
    try:
        data = json.loads(request.body)
        message = data.get("message")
        if message is not None:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(str(message) + "\n")
            return HttpResponse(status=200)
        return HttpResponse(status=400)
    except json.JSONDecodeError:
        return HttpResponse(status=400)

@require_http_methods(["GET"])
def retrieve_logs(request):
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            content = f.read()
        return HttpResponse(content, content_type="text/plain")
    except FileNotFoundError:
        return HttpResponse("", content_type="text/plain")