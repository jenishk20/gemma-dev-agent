import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from .models import Service

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
        
        service, created = Service.objects.update_or_create(
            service_id=service_id,
            defaults={'token': token, 'last_notification': timezone.now()}
        )
        
        # If the service existed but the token is different, we should technically 
        # decide if we allow token updates. Based on the schema, we update/register.
        return JsonResponse({}, status=200)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
def services_overview(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        token = data.get('token')
        
        if not token:
            return JsonResponse({'error': 'Invalid request payload'}, status=400)
        
        services = Service.objects.filter(token=token)
        result = []
        for s in services:
            result.append({
                'serviceId': s.service_id,
                'lastNotification': s.last_notification.isoformat()
            })
            
        return JsonResponse(result, safe=False, status=200)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)