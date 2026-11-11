import json
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.dateparse import parse_date
from django.db.models import Q
from .models import Click
import datetime

@csrf_exempt
def handle_click(request):
    if request.method == 'POST':
        Click.objects.create()
        return HttpResponse(status=201)
    return HttpResponse(status=405)

def retrieve_clicks(request):
    date_str = request.GET.get('date')
    direction = request.GET.get('direction')

    if not date_str or not direction:
        return JsonResponse({'error': 'Missing parameters'}, status=400)

    try:
        filter_date = parse_date(date_str)
        if not filter_date:
            raise ValueError("Invalid date format")
        
        # Convert date to datetime at start of day for comparison
        dt_filter = datetime.datetime.combine(filter_date, datetime.time.min)
    except Exception:
        return JsonResponse({'error': 'Invalid date format. Use YYYY-MM-DD'}, status=400)

    if direction not in ["<", ">", "<=", ">="]:
        return JsonResponse({'error': 'Invalid direction'}, status=400)

    # Construct query
    if direction == "<":
        queryset = Click.objects.filter(timestamp__lt=dt_filter)
    elif direction == ">":
        queryset = Click.objects.filter(timestamp__gt=dt_filter)
    elif direction == "<=":
        queryset = Click.objects.filter(timestamp__lte=dt_filter)
    elif direction == ">=":
        queryset = Click.objects.filter(timestamp__gte=dt_filter)
    else:
        return JsonResponse({'error': 'Invalid direction'}, status=400)

    clicks = list(queryset.values('id', 'timestamp'))
    
    if not clicks:
        return JsonResponse({'error': 'No clicks found'}, status=404)

    # Format timestamps to ISO 8601 strings
    result = []
    for c in clicks:
        result.append({
            'id': str(c['id']),
            'timestamp': c['timestamp'].isoformat()
        })

    return JsonResponse(result, safe=False)