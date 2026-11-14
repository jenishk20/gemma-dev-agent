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
        return JsonResponse({}, status=201)
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

        # Find cards that are associated with ALL provided phone numbers
        # We filter for the list of phones and group by credit_card, 
        # then check if the count of distinct phones equals the length of the input list.
        num_phones = len(set(phone_numbers))
        matching_cards = (
            CardPhoneAssociation.objects.filter(phone__in=phone_numbers)
            .values('credit_card')
            .annotate(phone_count=Count('phone'))
            .filter(phone_count=num_phones)
        )
        
        card_list = [item['credit_card'] for item in matching_cards]
        
        if not card_list:
            return JsonResponse({'error': 'Not found'}, status=404)
            
        return JsonResponse({'card_numbers': card_list}, status=200)
    except (json.JSONDecodeError, KeyError):
        return JsonResponse({'error': 'Invalid request'}, status=400)