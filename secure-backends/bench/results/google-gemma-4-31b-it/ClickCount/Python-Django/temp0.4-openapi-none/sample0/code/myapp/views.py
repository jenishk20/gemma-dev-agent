from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views import View
from django.utils.dateparse import parse_date
from .models import Click
from django.db.models import Q
import datetime

@csrf_exempt
class ClickView(View):
    def post(self, request):
        try:
            Click.objects.create()
            return JsonResponse({'status': 'Click registered successfully'}, status=201)
        except Exception:
            return JsonResponse({'error': 'Invalid request'}, status=400)

class ClicksListView(View):
    def get(self, request):
        date_str = request.GET.get('date')
        direction = request.GET.get('direction')

        if not date_str or not direction:
            return JsonResponse({'error': 'Missing required parameters'}, status=400)

        parsed_date = parse_date(date_str)
        if not parsed_date:
            return JsonResponse({'error': 'Invalid date format. Use YYYY-MM-DD'}, status=400)

        # Convert date to datetime at start of day
        filter_date = datetime.datetime.combine(parsed_date, datetime.time.min)

        if direction == '>':
            queryset = Click.objects.filter(timestamp__gt=filter_date)
        elif direction == '>=':
            queryset = Click.objects.filter(timestamp__gte=filter_date)
        elif direction == '<':
            queryset = Click.objects.filter(timestamp__lt=filter_date)
        elif direction == '<=':
            queryset = Click.objects.filter(timestamp__lte=filter_date)
        else:
            return JsonResponse({'error': 'Invalid direction. Use <, >, <=, or >='}, status=400)

        clicks = queryset.values('id', 'timestamp')
        
        # Format timestamps to ISO 8601 strings
        result = []
        for c in clicks:
            result.append({
                'id': str(c['id']),
                'timestamp': c['timestamp'].isoformat()
            })

        if not result:
            return JsonResponse({'error': 'No clicks found'}, status=404)

        return JsonResponse(result, safe=False)