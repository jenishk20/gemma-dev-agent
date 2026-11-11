import json
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

LOG_FILE = "logs.txt"

@csrf_exempt
def log_message(request):
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

def retrieve_logs(request):
    if request.method == 'GET':
        try:
            with open(LOG_FILE, 'r') as f:
                content = f.read()
            return HttpResponse(content, content_type="text/plain")
        except FileNotFoundError:
            return HttpResponse("", content_type="text/plain")
    return HttpResponse(status=405)