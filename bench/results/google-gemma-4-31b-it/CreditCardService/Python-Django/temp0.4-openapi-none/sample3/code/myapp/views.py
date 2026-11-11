import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import CardPhoneAssociation
from django.db.models import Count

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
        
        CardPhoneAssociation.objects.get_or_create(credit_card=credit_card, phone=phone)
        return JsonResponse({'status': 'Association created successfully'}, status=201)
    except (json.JSONDecodeError, TypeError):
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

        # A card must be associated with ALL given phone numbers.
        # We filter for associations involving any of the phones, 
        # group by card, and check if the count equals the number of unique phones requested.
        unique_phones = list(set(phone_numbers))
        num_phones = len(unique_phones)
        
        cards = (
            CardPhoneAssociation.objects
            .filter(phone__in=unique_phones)
            .values('credit_card')
            .annotate(phone_count=Count('phone'))
            .filter(phone_count=num_phones)
            .values_list('credit_card', flat=True)
        )
        
        card_list = list(cards)
        if not card_list:
            return JsonResponse({'error': 'Not found'}, status=404)
            
        return JsonResponse({'card_numbers': card_list}, status=200)
    except (json.JSONDecodeError, TypeError):
        return JsonResponse({'error': 'Invalid request'}, status=400)