import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from .models import ServiceStatus

@csrf_exempt
def heartbeat(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        service_id = data.get('serviceId')
        token = data.get('token')
        
        if not service_id or not token:
            return JsonResponse({'error': 'Invalid request payload'}, status=400)
        
        # Update or create the service record
        service, created = ServiceStatus.objects.update_or_create(
            service_id=service_id,
            defaults={'token': token, 'last_notification': timezone.now()}
        )
        
        # If the service existed but the token changed, we update it. 
        # The spec implies the token is used for auth, so we store the latest one.
        return JsonResponse({'status': 'Heartbeat registered successfully'}, status=200)
    except (json.JSONDecodeError, Exception):
        return JsonResponse({'error': 'Internal server error'}, status=500)

@csrf_exempt
def services(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        token = data.get('token')
        
        if not token:
            return JsonResponse({'error': 'Invalid request payload'}, status=400)
        
        # Get all services that match the provided token
        services_list = ServiceStatus.objects.filter(token=token)
        
        result = []
        for s in services_list:
            result.append({
                'serviceId': s.service_id,
                'lastNotification': s.last_notification.isoformat()
            })
            
        return JsonResponse(result, safe=False, status=200)
    except (json.JSONDecodeError, Exception):
        return JsonResponse({'error': 'Internal server error'}, status=500)