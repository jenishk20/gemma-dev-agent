import json
import jwt
import datetime
import os
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import UserProfile

SECRET_KEY = os.environ.get('APP_SECRET', 'django-insecure-default-key')

@csrf_exempt
def register(request):
    if request.method != 'POST':
        return JsonResponse({'message': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        email = data.get('email')
        password = data.get('password')
        name = data.get('name')

        if not email or not password or not name:
            return JsonResponse({'message': 'Missing required fields'}, status=400)

        if UserProfile.objects.filter(email=email).exists():
            return JsonResponse({'message': 'Email already in use or invalid data'}, status=400)

        UserProfile.objects.create(email=email, password=password, name=name)
        return JsonResponse({'message': 'Registration successful'}, status=201)
    except Exception:
        return JsonResponse({'message': 'Bad Request'}, status=400)

@csrf_exempt
def login(request):
    if request.method != 'POST':
        return JsonResponse({'message': 'Method not allowed'}, status=405)

    try:
        data = json.loads(request.body)
        email = data.get('email')
        password = data.get('password')

        user = UserProfile.objects.filter(email=email, password=password).first()
        if not user:
            return JsonResponse({'message': 'Invalid email or password'}, status=401)

        token = jwt.encode({
            'user_id': user.id,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
        }, SECRET_KEY, algorithm='HS256')

        return JsonResponse({
            'token': token,
            'message': 'Login successful'
        }, status=200)
    except Exception:
        return JsonResponse({'message': 'Bad Request'}, status=400)