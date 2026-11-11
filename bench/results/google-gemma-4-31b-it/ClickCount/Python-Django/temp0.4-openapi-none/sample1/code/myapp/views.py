from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.dateparse import parse_date
from .models import Click
from django.db.models import Q
import datetime

@csrf_exempt
def click_view(request):
    if request.method == 'POST':
        Click.objects.create()
        return HttpResponse(status=201)
    return HttpResponse(status=405)

def clicks_view(request):
    if request.method != 'GET':
        return HttpResponse(status=405)

    date_str = request.GET.get('date')
    direction = request.GET.get('direction')

    if not date_str or not direction:
        return JsonResponse({'error': 'Missing parameters'}, status=400)

    try:
        parsed_date = parse_date(date_str)
        if not parsed_date:
            raise ValueError()
        # Convert date to datetime at start of day
        filter_date = datetime.datetime.combine(parsed_date, datetime.time.min)
    except ValueError:
        return JsonResponse({'error': 'Invalid date format'}, status=400)

    if direction == '>':
        queryset = Click.objects.filter(timestamp__gt=filter_date)
    elif direction == '<':
        queryset = Click.objects.filter(timestamp__lt=filter_date)
    elif direction == '>=':
        queryset = Click.objects.filter(timestamp__gte=filter_date)
    elif direction == '<=':
        queryset = Click.objects.filter(timestamp__lte=filter_date)
    else:
        return JsonResponse({'error': 'Invalid direction'}, status=400)

    clicks = list(queryset.values('id', 'timestamp'))
    
    if not clicks:
        return JsonResponse({'error': 'No clicks found'}, status=404)

    # Format timestamps to ISO string
    results = []
    for c in clicks:
        results.append({
            'id': str(c['id']),
            'timestamp': c['timestamp'].isoformat()
        })

    return JsonResponse(results, safe=False)