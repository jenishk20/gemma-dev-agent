import jwt
import os
import datetime
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password, check_password
from .models import SecretStorage
from django.views import View

APP_SECRET = os.environ.get('APP_SECRET', 'django-insecure-default-key')

def get_token_from_header(request):
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return None
    token = auth_header.split(' ')[1]
    try:
        payload = jwt.decode(token, APP_SECRET, algorithms=['HS256'])
        return payload
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None

@csrf_exempt
def register(request):
    if request.method == 'POST':
        try:
            import json
            data = json.loads(request.body)
            email = data.get('email')
            username = data.get('username')
            password = data.get('password')

            if not email or not username or not password:
                return JsonResponse({'message': 'Missing fields'}, status=400)
            
            if User.objects.filter(email=email).exists() or User.objects.filter(username=username).exists():
                return JsonResponse({'message': 'Email or username already in use'}, status=400)

            user = User.objects.create_user(username=username, email=email, password=password)
            return JsonResponse({'message': 'Registration successful'}, status=201)
        except Exception as e:
            return JsonResponse({'message': str(e)}, status=400)
    return JsonResponse({'message': 'Method not allowed'}, status=405)

@csrf_exempt
def login(request):
    if request.method == 'POST':
        try:
            import json
            data = json.loads(request.body)
            email = data.get('email')
            password = data.get('password')

            user = User.objects.filter(email=email).first()
            if user and check_password(password, user.password):
                token = jwt.encode({
                    'user_id': user.id,
                    'username': user.username,
                    'exp': datetime.datetime.utcnow() + datetime.timedelta(days=1)
                }, APP_SECRET, algorithm='HS256')
                return JsonResponse({'token': token, 'message': 'Login successful'}, status=200)
            
            return JsonResponse({'message': 'Invalid email or password'}, status=401)
        except Exception:
            return JsonResponse({'message': 'Invalid request'}, status=400)
    return JsonResponse({'message': 'Method not allowed'}, status=405)

@csrf_exempt
def set_secret(request):
    if request.method == 'POST':
        payload = get_token_from_header(request)
        if not payload:
            return JsonResponse({'message': 'Invalid authentication token'}, status=401)

        try:
            import json
            data = json.loads(request.body)
            username = data.get('username')
            secret = data.get('secret')

            # Ensure the token belongs to the user they are trying to set a secret for
            if payload.get('username') != username:
                return JsonResponse({'message': 'Unauthorized access to this user'}, status=401)

            user = User.objects.get(username=username)
            SecretStorage.objects.update_or_create(user=user, defaults={'secret_text': secret})
            return JsonResponse({'message': 'Secret has been set successfully'}, status=200)
        except Exception as e:
            return JsonResponse({'message': str(e)}, status=400)
    return JsonResponse({'message': 'Method not allowed'}, status=405)

@csrf_exempt
def get_secret(request):
    if request.method == 'GET':
        payload = get_token_from_header(request)
        if not payload:
            return JsonResponse({'message': 'Invalid authentication token'}, status=401)

        username = request.GET.get('username')
        if not username:
            return JsonResponse({'message': 'Username parameter is required'}, status=400)

        # Ensure the token belongs to the user they are trying to retrieve a secret for
        if payload.get('username') != username:
            return JsonResponse({'message': 'Unauthorized access to this user'}, status=401)

        try:
            user = User.objects.get(username=username)
            secret_obj = SecretStorage.objects.get(user=user)
            return JsonResponse({'secret': secret_obj.secret_text}, status=200)
        except SecretStorage.DoesNotExist:
            return JsonResponse({'secret': 'No secret found'}, status=200)
        except User.DoesNotExist:
            return JsonResponse({'message': 'User not found'}, status=404)
    return JsonResponse({'message': 'Method not allowed'}, status=405)