import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Count
from .models import CardAssociation

@csrf_exempt
def associate_card(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        credit_card = data.get('credit_card')
        phone = data.get('phone')
        
        if not credit_card or not phone:
            return JsonResponse({'error': 'Invalid request'}, status=400)
        
        CardAssociation.objects.get_or_create(credit_card=credit_card, phone=phone)
        return JsonResponse({'status': 'Association created successfully'}, status=201)
    except (json.JSONDecodeError, KeyError):
        return JsonResponse({'error': 'Invalid request'}, status=400)

@csrf_exempt
def retrieve_cards(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        phone_numbers = data.get('phone_numbers')
        
        if not isinstance(phone_numbers, list):
            return JsonResponse({'error': 'Invalid request'}, status=400)
        
        if not phone_numbers:
            return JsonResponse({'card_numbers': []}, status=200)

        # Find cards that are associated with ALL the provided phone numbers
        # We filter for any of the phones, then group by card and count if the number of 
        # distinct phones matches the length of the input list.
        unique_phones = list(set(phone_numbers))
        count_needed = len(unique_phones)
        
        cards = CardAssociation.objects.filter(phone__in=unique_phones) \
            .values('credit_card') \
            .annotate(phone_count=Count('phone')) \
            .filter(phone_count=count_needed)
        
        card_list = [c['credit_card'] for c in cards]
        
        if not card_list:
            return JsonResponse({'error': 'Not found'}, status=404)
            
        return JsonResponse({'card_numbers': card_list}, status=200)
    except (json.JSONDecodeError, KeyError):
        return JsonResponse({'error': 'Invalid request'}, status=400)