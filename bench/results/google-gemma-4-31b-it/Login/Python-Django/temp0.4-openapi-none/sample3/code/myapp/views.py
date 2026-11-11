import json
import jwt
import datetime
import os
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from django.contrib.auth import authenticate

SECRET_KEY = os.environ.get('APP_SECRET', 'django-insecure-default-key')

def generate_token(user):
    payload = {
        'user_id': user.id,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(days=1),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm='HS256')

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

        if User.objects.filter(email=email).exists():
            return JsonResponse({'message': 'Email already in use or invalid data'}, status=400)

        user = User.objects.create_user(username=email, email=email, password=password)
        user.first_name = name
        user.save()

        return JsonResponse({'message': 'Registration successful'}, status=201)
    except Exception:
        return JsonResponse({'message': 'Invalid data'}, status=400)

@csrf_exempt
def login(request):
    if request.method != 'POST':
        return JsonResponse({'message': 'Method not allowed'}, status=405)

    try:
        data = json.loads(request.body)
        email = data.get('email')
        password = data.get('password')

        if not email or not password:
            return JsonResponse({'message': 'Invalid email or password'}, status=401)

        # Django's authenticate requires username. We used email as username during registration.
        user = authenticate(username=email, password=password)

        if user is not None:
            token = generate_token(user)
            return JsonResponse({
                'token': token,
                'message': 'Login successful'
            }, status=200)
        else:
            return JsonResponse({'message': 'Invalid email or password'}, status=401)
    except Exception:
        return JsonResponse({'message': 'Invalid request'}, status=401)