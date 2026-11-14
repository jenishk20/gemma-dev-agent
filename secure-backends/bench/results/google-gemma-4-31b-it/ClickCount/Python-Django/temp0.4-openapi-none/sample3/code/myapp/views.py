import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.dateparse import parse_date
from .models import Click
from django.db.models import Q
import datetime

@csrf_exempt
def click_handler(request):
    if request.method == 'POST':
        Click.objects.create()
        return JsonResponse({'status': 'Click registered successfully'}, status=201)
    return JsonResponse({'error': 'Method not allowed'}, status=405)

def clicks_handler(request):
    date_str = request.GET.get('date')
    direction = request.GET.get('direction')

    if not date_str or not direction:
        return JsonResponse({'error': 'Missing date or direction parameter'}, status=400)

    parsed_date = parse_date(date_str)
    if not parsed_date:
        return JsonResponse({'error': 'Invalid date format. Use YYYY-MM-DD'}, status=400)

    # Convert date to datetime at start of day for comparison
    filter_date = datetime.datetime.combine(parsed_date, datetime.time.min)

    if direction == '>':
        clicks = Click.objects.filter(timestamp__gt=filter_date)
    elif direction == '>=':
        clicks = Click.objects.filter(timestamp__gte=filter_date)
    elif direction == '<':
        clicks = Click.objects.filter(timestamp__lt=filter_date)
    elif direction == '<=':
        clicks = Click.objects.filter(timestamp__lte=filter_date)
    else:
        return JsonResponse({'error': 'Invalid direction. Use <, >, <=, or >='}, status=400)

    if not clicks.exists():
        return JsonResponse({'error': 'No clicks found'}, status=404)

    data = []
    for c in clicks:
        data.append({
            'id': str(c.id),
            'timestamp': c.timestamp.isoformat()
        })
    
    return JsonResponse(data, safe=False)