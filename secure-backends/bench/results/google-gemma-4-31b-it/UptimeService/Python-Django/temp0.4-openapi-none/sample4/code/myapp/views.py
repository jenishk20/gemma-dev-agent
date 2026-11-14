import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.dateparse import parse_datetime
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
        
        # Update or create the service status
        service, created = ServiceStatus.objects.update_or_create(
            service_id=service_id,
            defaults={'token': token}
        )
        # last_notification is auto_now=True, so it updates on save()
        service.save()
        
        return JsonResponse({'status': 'Heartbeat registered successfully'}, status=200)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
def services(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        token = data.get('token')
        
        if not token:
            return JsonResponse({'error': 'Invalid request payload'}, status=400)
        
        # Filter services that match the provided token
        services_list = ServiceStatus.objects.filter(token=token)
        
        response_data = []
        for s in services_list:
            response_data.append({
                'serviceId': s.service_id,
                'lastNotification': s.last_notification.isoformat()
            })
            
        return JsonResponse(response_data, safe=False, status=200)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)