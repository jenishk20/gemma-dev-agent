import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from .models import CardAssociation
from django.db.models import Count

@csrf_exempt
@require_http_methods(["POST"])
def associate_card(request):
    try:
        data = json.loads(request.body)
        credit_card = data.get('credit_card')
        phone = data.get('phone')

        if not credit_card or not phone:
            return JsonResponse({'error': 'Invalid request'}, status=400)

        CardAssociation.objects.get_or_create(credit_card=credit_card, phone=phone)
        return JsonResponse({}, status=201)
    except (json.JSONDecodeError, TypeError):
        return JsonResponse({'error': 'Invalid request'}, status=400)

@csrf_exempt
@require_http_methods(["POST"])
def retrieve_cards(request):
    try:
        data = json.loads(request.body)
        phone_numbers = data.get('phone_numbers')

        if not isinstance(phone_numbers, list):
            return JsonResponse({'error': 'Invalid request'}, status=400)

        if not phone_numbers:
            return JsonResponse({'card_numbers': []}, status=200)

        # Find cards associated with ALL provided phone numbers
        # We filter for any of the phones, then group by card and count distinct phones
        # The count must equal the number of unique phones requested
        unique_phones = list(set(phone_numbers))
        count_required = len(unique_phones)

        cards = (
            CardAssociation.objects.filter(phone__in=unique_phones)
            .values('credit_card')
            .annotate(phone_count=Count('phone'))
            .filter(phone_count=count_required)
            .values_list('credit_card', flat=True)
        )

        if not cards.exists():
            return JsonResponse({'error': 'Not found'}, status=404)

        return JsonResponse({'card_numbers': list(cards)}, status=200)
    except (json.JSONDecodeError, TypeError):
        return JsonResponse({'error': 'Invalid request'}, status=400)