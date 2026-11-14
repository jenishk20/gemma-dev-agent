import json
import jwt
import datetime
import os
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password, check_password

User = get_user_model()
SECRET_KEY = os.environ.get('APP_SECRET', 'django-insecure-default-key')

def generate_token(user):
    payload = {
        'user_id': user.id,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24),
        'iat': datetime.datetime.utcnow(),
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
            return JsonResponse({'message': 'Email, password, and name are required'}, status=400)
        
        if User.objects.filter(email=email).exists():
            return JsonResponse({'message': 'Email already in use'}, status=400)

        # Using name as username for simplicity in AbstractUser
        user = User.objects.create_user(
            username=name, 
            email=email, 
            password=password
        )
        return JsonResponse({'message': 'Registration successful'}, status=201)
    except Exception as e:
        return JsonResponse({'message': str(e)}, status=400)

@csrf_exempt
def login(request):
    if request.method != 'POST':
        return JsonResponse({'message': 'Method not allowed'}, status=405)

    try:
        data = json.loads(request.body)
        email = data.get('email')
        password = data.get('password')

        if not email or not password:
            return JsonResponse({'message': 'Email and password are required'}, status=400)

        try:
            user = User.objects.get(email=email)
            if check_password(password, user.password):
                token = generate_token(user)
                return JsonResponse({
                    'token': token,
                    'message': 'Login successful'
                }, status=200)
        except User.DoesNotExist:
            pass

        return JsonResponse({'message': 'Invalid email or password'}, status=401)
    except Exception as e:
        return JsonResponse({'message': str(e)}, status=400)