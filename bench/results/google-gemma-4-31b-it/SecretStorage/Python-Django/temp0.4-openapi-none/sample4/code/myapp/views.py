import jwt
import datetime
import os
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from .models import Secret
from django.views.decorators.http import require_http_methods

APP_SECRET = os.environ.get('APP_SECRET', 'django-insecure-default-key')

def generate_token(user):
    payload = {
        'user_id': user.id,
        'username': user.username,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(days=1),
        'iat': datetime.datetime.utcnow(),
    }
    return jwt.encode(payload, APP_SECRET, algorithm='HS256')

def verify_token(request):
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return None
    
    token = auth_header.split(' ')[1]
    try:
        payload = jwt.decode(token, APP_SECRET, algorithms=['HS256'])
        return User.objects.get(id=payload['user_id'])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, User.DoesNotExist):
        return None

@csrf_exempt
@require_http_methods(["POST"])
def register(request):
    try:
        import json
        data = json.loads(request.body)
        email = data.get('email')
        username = data.get('username')
        password = data.get('password')

        if not email or not username or not password:
            return JsonResponse({'message': 'Invalid data'}, status=400)
        
        if User.objects.filter(email=email).exists() or User.objects.filter(username=username).exists():
            return JsonResponse({'message': 'Email or username already in use'}, status=400)

        user = User.objects.create_user(username=username, email=email, password=password)
        return JsonResponse({'message': 'Registration successful'}, status=201)
    except Exception:
        return JsonResponse({'message': 'Bad Request'}, status=400)

@csrf_exempt
@require_http_methods(["POST"])
def login(request):
    try:
        import json
        data = json.loads(request.body)
        email = data.get('email')
        password = data.get('password')

        user = User.objects.filter(email=email).first()
        if user and user.check_password(password):
            token = generate_token(user)
            return JsonResponse({'token': token, 'message': 'Login successful'}, status=200)
        
        return JsonResponse({'message': 'Invalid email or password'}, status=401)
    except Exception:
        return JsonResponse({'message': 'Bad Request'}, status=400)

@csrf_exempt
@require_http_methods(["POST"])
def set_secret(request):
    user = verify_token(request)
    if not user:
        return JsonResponse({'message': 'Invalid authentication token'}, status=401)

    try:
        import json
        data = json.loads(request.body)
        username = data.get('username')
        secret_text = data.get('secret')

        if username != user.username:
            return JsonResponse({'message': 'Username mismatch'}, status=401)

        secret_obj, created = Secret.objects.update_or_create(
            user=user, 
            defaults={'secret_text': secret_text}
        )
        return JsonResponse({'message': 'Secret has been set successfully'}, status=200)
    except Exception:
        return JsonResponse({'message': 'Bad Request'}, status=400)

@csrf_exempt
@require_http_methods(["GET"])
def get_secret(request):
    user = verify_token(request)
    if not user:
        return JsonResponse({'message': 'Invalid authentication token'}, status=401)

    username = request.GET.get('username')
    if not username:
        return JsonResponse({'message': 'Username is required'}, status=400)

    if username != user.username:
        return JsonResponse({'message': 'Unauthorized access to this secret'}, status=401)

    try:
        secret_obj = Secret.objects.get(user=user)
        return JsonResponse({'secret': secret_obj.secret_text}, status=200)
    except Secret.DoesNotExist:
        return JsonResponse({'secret': ''}, status=200)