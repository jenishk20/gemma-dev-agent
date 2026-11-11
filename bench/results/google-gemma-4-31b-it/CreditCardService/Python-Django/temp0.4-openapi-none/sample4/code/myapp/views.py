import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Count
from .models import CreditCard, Phone, Association

@csrf_exempt
def associate_card(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        card_num = data.get('credit_card')
        phone_num = data.get('phone')
        
        if not card_num or not phone_num:
            return JsonResponse({'error': 'Invalid request'}, status=400)
        
        card, _ = CreditCard.objects.get_or_create(card_number=card_num)
        phone, _ = Phone.objects.get_or_create(phone_number=phone_num)
        
        Association.objects.get_or_create(card=card, phone=phone)
        
        return JsonResponse({'status': 'Association created successfully'}, status=201)
    except Exception:
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

        # Find cards associated with ALL provided phone numbers
        # We filter associations by the list of phones, then group by card 
        # and filter for those that have a count equal to the number of unique phones requested.
        unique_phones = list(set(phone_numbers))
        num_phones = len(unique_phones)
        
        cards = CreditCard.objects.filter(
            association__phone__phone_number__in=unique_phones
        ).annotate(
            num_matches=Count('association')
        ).filter(
            num_matches=num_phones
        ).values_list('card_number', flat=True)
        
        if not cards:
            return JsonResponse({'error': 'Not found'}, status=404)
            
        return JsonResponse({'card_numbers': list(cards)}, status=200)
    except Exception:
        return JsonResponse({'error': 'Invalid request'}, status=400)