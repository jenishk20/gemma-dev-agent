import jwt
import datetime
import os
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from .models import Secret
from django.core.exceptions import ValidationError

SECRET_KEY = os.environ.get('APP_SECRET', 'django-insecure-default-key')

def create_token(user):
    payload = {
        'user_id': user.id,
        'username': user.username,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(days=1)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm='HS256')

def verify_token(request):
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return None
    
    token = auth_header.split(' ')[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        return User.objects.get(id=payload['user_id'])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, User.DoesNotExist):
        return None

@csrf_exempt
def register(request):
    if request.method != 'POST':
        return JsonResponse({'message': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        email = data.get('email')
        username = data.get('username')
        password = data.get('password')
        
        if not email or not username or not password:
            return JsonResponse({'message': 'Missing fields'}, status=400)
        
        if User.objects.filter(email=email).exists() or User.objects.filter(username=username).exists():
            return JsonResponse({'message': 'Email already in use or invalid data'}, status=400)
        
        user = User.objects.create_user(username=username, email=email, password=password)
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
        
        user = User.objects.filter(email=email).first()
        if user and user.check_password(password):
            token = create_token(user)
            return JsonResponse({'token': token, 'message': 'Login successful'}, status=200)
        
        return JsonResponse({'message': 'Invalid email or password'}, status=401)
    except Exception:
        return JsonResponse({'message': 'Invalid request'}, status=400)

@csrf_exempt
def set_secret(request):
    if request.method != 'POST':
        return JsonResponse({'message': 'Method not allowed'}, status=405)
    
    user = verify_token(request)
    if not user:
        return JsonResponse({'message': 'Invalid authentication token'}, status=401)
    
    try:
        data = json.loads(request.body)
        username = data.get('username')
        secret_text = data.get('secret')
        
        if username != user.username:
            return JsonResponse({'message': 'Username mismatch'}, status=401)
        
        Secret.objects.update_or_create(user=user, defaults={'secret_text': secret_text})
        return JsonResponse({'message': 'Secret has been set successfully'}, status=200)
    except Exception:
        return JsonResponse({'message': 'Invalid request'}, status=400)

@csrf_exempt
def get_secret(request):
    if request.method != 'GET':
        return JsonResponse({'message': 'Method not allowed'}, status=405)
    
    user = verify_token(request)
    if not user:
        return JsonResponse({'message': 'Invalid authentication token'}, status=401)
    
    username = request.GET.get('username')
    if not username or username != user.username:
        return JsonResponse({'message': 'Invalid authentication token'}, status=401)
    
    try:
        secret_obj = Secret.objects.get(user=user)
        return JsonResponse({'secret': secret_obj.secret_text}, status=200)
    except Secret.DoesNotExist:
        return JsonResponse({'secret': ''}, status=200)