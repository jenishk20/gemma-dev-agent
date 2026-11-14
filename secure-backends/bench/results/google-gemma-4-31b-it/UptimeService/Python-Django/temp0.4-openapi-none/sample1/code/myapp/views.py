import json
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from .models import ServiceStatus

@csrf_exempt
def heartbeat(request):
    if request.method != 'POST':
        return HttpResponse(status=405)
    
    try:
        data = json.loads(request.body)
        service_id = data.get('serviceId')
        token = data.get('token')
        
        if not service_id or not token:
            return JsonResponse({'error': 'Invalid request payload'}, status=400)
        
        # Update or create the service status
        ServiceStatus.objects.update_or_create(
            service_id=service_id,
            defaults={'token': token, 'last_notification': timezone.now()}
        )
        
        return HttpResponse(status=200)
    except (json.JSONDecodeError, Exception):
        return JsonResponse({'error': 'Internal server error'}, status=500)

@csrf_exempt
def services_overview(request):
    if request.method != 'POST':
        return HttpResponse(status=405)
    
    try:
        data = json.loads(request.body)
        token = data.get('token')
        
        if not token:
            return JsonResponse({'error': 'Invalid request payload'}, status=400)
        
        services = ServiceStatus.objects.filter(token=token)
        result = [
            {
                'serviceId': s.service_id,
                'lastNotification': s.last_notification.isoformat()
            } for s in services
        ]
        
        return JsonResponse(result, safe=False, status=200)
    except (json.JSONDecodeError, Exception):
        return JsonResponse({'error': 'Internal server error'}, status=500)