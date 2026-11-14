import json
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Message

@csrf_exempt
def messages_view(request):
    if request.method == 'GET':
        limit = int(request.GET.get('limit', 10))
        offset = int(request.GET.get('offset', 0))
        sort = request.GET.get('sort', 'DESC').upper()

        queryset = Message.objects.all()
        
        if sort == 'ASC':
            queryset = queryset.order_by('created_at')
        else:
            queryset = queryset.order_by('-created_at')

        messages = queryset[offset:offset+limit]
        
        # The OpenAPI schema specifies text/html response for GET /messages
        html = "<h1>Forum Messages</h1><ul>"
        for msg in messages:
            html += f"<li><b>{msg.username}</b>: {msg.content}</li>"
        html += "</ul>"
        
        return HttpResponse(html, content_type="text/html")

    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            username = data.get('username')
            content = data.get('content')
            
            if not username or not content:
                return HttpResponse("Invalid input", status=400)
            
            Message.objects.create(username=username, content=content)
            return HttpResponse("Successful operation", status=200)
        except (json.JSONDecodeError, TypeError):
            return HttpResponse("Invalid input", status=400)

    return HttpResponse("Method Not Allowed", status=405)