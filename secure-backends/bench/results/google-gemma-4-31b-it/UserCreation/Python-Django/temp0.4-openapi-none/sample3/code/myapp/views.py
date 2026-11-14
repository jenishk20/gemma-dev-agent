import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from .models import Invitation
import uuid

@csrf_exempt
def invite_user(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        email = data.get('email')
        if not email:
            return JsonResponse({'message': 'Email is required'}, status=400)
        
        # Get existing invitation or create a new one
        invitation, created = Invitation.objects.get_or_create(email=email)
        
        # The schema requires a string invite_id. 
        # If it was created via get_or_create, invite_id is already set.
        # We ensure it's a string.
        invite_id_str = str(invitation.invite_id)
        
        return JsonResponse({
            'invite_id': invite_id_str,
            'message': 'Invitation created successfully' if created else 'Invitation retrieved'
        }, status=200)
    except Exception as e:
        return JsonResponse({'message': str(e)}, status=400)

@csrf_exempt
def create_user(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        invite_id = data.get('invite_id')
        user_name = data.get('user_name')
        password = data.get('password')
        
        if not invite_id or not user_name or not password:
            return JsonResponse({'message': 'Missing required fields'}, status=400)
        
        try:
            invitation = Invitation.objects.get(invite_id=invite_id, used=False)
        except Invitation.DoesNotExist:
            return JsonResponse({'message': 'Invalid invite_id'}, status=401)
        
        if User.objects.filter(username=user_name).exists():
            return JsonResponse({'message': 'Username already exists. Try providing different username.'}, status=400)
        
        # Create the user
        user = User.objects.create_user(username=user_name, password=password)
        # Mark invitation as used
        invitation.used = True
        invitation.save()
        
        return JsonResponse({'message': 'User created'}, status=200)
        
    except json.JSONDecodeError:
        return JsonResponse({'message': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'message': str(e)}, status=400)