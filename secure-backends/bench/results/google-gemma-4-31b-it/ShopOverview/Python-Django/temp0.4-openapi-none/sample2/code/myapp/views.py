import json
import csv
import io
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Merchant, Ware
from django.shortcuts import render

def get_authenticated_merchant(request):
    auth_cookie = request.COOKIES.get('AUTH_COOKIE')
    if not auth_cookie:
        return None
    try:
        # In this simple implementation, we store the email in the cookie
        return Merchant.objects.get(email=auth_cookie)
    except Merchant.DoesNotExist:
        return None

@csrf_exempt
def register_merchant(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        email = data.get('email')
        name = data.get('name')
        password = data.get('password')
        
        if not all([email, name, password]):
            return JsonResponse({'error': 'Missing required fields'}, status=400)
        
        if Merchant.objects.filter(email=email).exists():
            return JsonResponse({'error': 'Merchant already exists'}, status=400)
            
        Merchant.objects.create(email=email, name=name, password=password)
        return HttpResponse(status=201)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@csrf_exempt
def login_merchant(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        email = data.get('email')
        password = data.get('password')
        
        merchant = Merchant.objects.filter(email=email, password=password).first()
        if merchant:
            response = JsonResponse('Login successful', status=200)
            response.set_cookie('AUTH_COOKIE', merchant.email)
            return response
        else:
            return JsonResponse({'error': 'Invalid email or password'}, status=401)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@csrf_exempt
def upload_wares(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    merchant = get_authenticated_merchant(request)
    if not merchant:
        return JsonResponse({'error': 'Unauthorized'}, status=401)
    
    try:
        data = json.loads(request.body)
        csv_string = data.get('csv', '')
        
        f = io.StringIO(csv_string)
        reader = csv.reader(f)
        
        for row in reader:
            if len(row) != 3:
                return JsonResponse({'error': 'Invalid CSV format'}, status=400)
            
            name, description, price_str = row
            Ware.objects.create(
                merchant=merchant,
                name=name,
                description=description,
                price=float(price_str)
            )
        return HttpResponse(status=200)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

def list_wares(request):
    merchant = get_authenticated_merchant(request)
    if not merchant:
        return JsonResponse({'error': 'Unauthorized'}, status=401)
    
    min_price = request.GET.get('minPrice')
    max_price = request.GET.get('maxPrice')
    
    wares = Ware.objects.all().select_related('merchant')
    
    if min_price:
        wares = wares.filter(price__gte=float(min_price))
    if max_price:
        wares = wares.filter(price__lte=float(max_price))
    
    # Manual HTML table generation as requested by OpenAPI response description
    html = '<table><tr><th>Name</th><th>Price</th><th>Description</th><th>Merchant</th></tr>'
    for ware in wares:
        html += f'<tr><td>{ware.name}</td><td>{ware.price}</td><td>{ware.description}</td><td>{ware.merchant.email}</td></tr>'
    html += '</table>'
    
    return HttpResponse(html, content_type='text/html')