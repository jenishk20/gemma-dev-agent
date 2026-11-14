import json
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Message

@csrf_exempt
def messages_view(request):
    if request.method == 'GET':
        # Query parameters
        limit = int(request.GET.get('limit', 10))
        offset = int(request.GET.get('offset', 0))
        sort = request.GET.get('sort', 'DESC').upper()

        # Ordering
        order_field = '-created_at' if sort == 'DESC' else 'created_at'
        
        messages_qs = Message.objects.order_by(order_field)[offset:offset+limit]
        
        # The OpenAPI schema specifies text/html response for GET /messages
        # We will render a simple HTML list of messages
        html_content = "<html><body><h1>Forum Messages</h1><ul>"
        for msg in messages_qs:
            html_content += f"<li><strong>{msg.username}</strong>: {msg.content}</li>"
        html_content += "</ul></body></html>"
        
        return HttpResponse(html_content, content_type="text/html")

    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            username = data.get('username')
            content = data.get('content')
            
            if not username or not content:
                return HttpResponse("Invalid input", status=400)
            
            Message.objects.create(username=username, content=content)
            return HttpResponse("Successful operation", status=200)
        except (json.JSONDecodeError, AttributeError):
            return HttpResponse("Invalid input", status=400)

    return HttpResponse("Method Not Allowed", status=405)