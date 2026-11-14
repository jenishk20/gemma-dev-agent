import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from .models import Invitation

@csrf_exempt
def invite_user(request):
    if request.method != 'POST':
        return JsonResponse({'message': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        email = data.get('email')
        if not email:
            return JsonResponse({'message': 'Email is required'}, status=400)
        
        invite, created = Invitation.objects.get_or_create(email=email)
        
        return JsonResponse({
            'invite_id': str(invite.invite_id),
            'message': 'Invitation created successfully' if created else 'Invitation already exists'
        }, status=200)
    except Exception as e:
        return JsonResponse({'message': str(e)}, status=400)

@csrf_exempt
def create_user(request):
    if request.method != 'POST':
        return JsonResponse({'message': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        invite_id = data.get('invite_id')
        user_name = data.get('user_name')
        password = data.get('password')

        if not all([invite_id, user_name, password]):
            return JsonResponse({'message': 'Missing required fields'}, status=400)

        try:
            invite = Invitation.objects.get(invite_id=invite_id, used=False)
        except Invitation.DoesNotExist:
            return JsonResponse({'message': 'Invalid invite_id'}, status=401)

        if User.objects.filter(username=user_name).exists():
            return JsonResponse({'message': 'Username already exists. Try providing different username.'}, status=400)

        user = User.objects.create_user(username=user_name, password=password)
        invite.used = True
        invite.save()

        return JsonResponse({'message': 'User created'}, status=200)
    except Exception as e:
        return JsonResponse({'message': str(e)}, status=400)