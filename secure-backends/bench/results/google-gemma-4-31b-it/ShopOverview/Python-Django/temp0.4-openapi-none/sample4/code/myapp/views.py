import json
import csv
import io
import jwt
import os
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from .models import Ware
from django.shortcuts import render

SECRET_KEY = os.environ.get('APP_SECRET', 'django-insecure-default-key')

def get_user_from_cookie(request):
    token = request.COOKIES.get('AUTH_COOKIE')
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        return User.objects.get(id=payload['user_id'])
    except Exception:
        return None

@csrf_exempt
def register_merchant(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        email = data['email']
        name = data['name']
        password = data['password']
        
        if User.objects.filter(email=email).exists():
            return JsonResponse({'error': 'Email already exists'}, status=400)
            
        user = User.objects.create_user(username=email, email=email, password=password, first_name=name)
        return JsonResponse({'message': 'Merchant registered successfully'}, status=201)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@csrf_exempt
def login_merchant(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        email = data['email']
        password = data['password']
        
        user = User.objects.filter(email=email).first()
        if user and user.check_password(password):
            token = jwt.encode({'user_id': user.id}, SECRET_KEY, algorithm='HS256')
            response = JsonResponse('Login successful', status=200)
            response.set_cookie('AUTH_COOKIE', token, httponly=True)
            return response
        else:
            return JsonResponse({'error': 'Invalid email or password'}, status=401)
    except Exception:
        return JsonResponse({'error': 'Invalid input'}, status=400)

@csrf_exempt
def upload_wares(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    user = get_user_from_cookie(request)
    if not user:
        return JsonResponse({'error': 'Unauthorized'}, status=401)
    
    try:
        data = json.loads(request.body)
        csv_content = data.get('csv', '')
        f = io.StringIO(csv_content)
        reader = csv.DictReader(f, fieldnames=['name', 'description', 'price'])
        
        for row in reader:
            Ware.objects.create(
                name=row['name'],
                description=row['description'],
                price=float(row['price']),
                merchant=user
            )
        return JsonResponse({'message': 'Wares uploaded successfully'}, status=200)
    except Exception as e:
        return JsonResponse({'error': f'Invalid CSV format: {str(e)}'}, status=400)

def get_wares(request):
    # The schema says security: cookieAuth, but the response is HTML.
    # We check for the cookie as per schema.
    if not get_user_from_cookie(request):
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    min_price = request.GET.get('minPrice')
    max_price = request.GET.get('maxPrice')
    
    wares = Ware.objects.all().select_related('merchant')
    
    if min_price:
        wares = wares.filter(price__gte=float(min_price))
    if max_price:
        wares = wares.filter(price__lte=float(max_price))
        
    # Manual HTML table construction as requested by the schema's response description
    html = '<table><tr><th>Name</th><th>Price</th><th>Description</th><th>Merchant</th></tr>'
    for w in wares:
        html += f'<tr><td>{w.name}</td><td>{w.price}</td><td>{w.description}</td><td>{w.merchant.email}</td></tr>'
    html += '</table>'
    
    return HttpResponse(html, content_type='text/html')