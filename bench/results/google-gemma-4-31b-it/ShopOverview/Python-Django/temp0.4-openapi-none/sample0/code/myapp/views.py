import json
import csv
import io
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import get_user_model
from .models import Merchant, Ware

# Simple session-like auth using a cookie containing the merchant email
# In a real app, we would use JWT or Django's session framework.
# The schema requires a cookie named AUTH_COOKIE.

def get_authenticated_merchant(request):
    email = request.COOKIES.get('AUTH_COOKIE')
    if email:
        try:
            return Merchant.objects.get(email=email)
        except Merchant.DoesNotExist:
            return None
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
            return JsonResponse({'error': 'Missing fields'}, status=400)
        
        if Merchant.objects.filter(email=email).exists():
            return JsonResponse({'error': 'Merchant already exists'}, status=400)
            
        Merchant.objects.create(email=email, name=name, password=password)
        return JsonResponse({'message': 'Merchant registered successfully'}, status=201)
    except Exception:
        return JsonResponse({'error': 'Invalid input'}, status=400)

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
            response.set_cookie('AUTH_COOKIE', email)
            return response
        else:
            return JsonResponse({'error': 'Invalid email or password'}, status=401)
    except Exception:
        return JsonResponse({'error': 'Invalid input'}, status=400)

@csrf_exempt
def upload_wares(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    merchant = get_authenticated_merchant(request)
    if not merchant:
        return JsonResponse({'error': 'Unauthorized'}, status=401)
    
    try:
        data = json.loads(request.body)
        csv_content = data.get('csv', '')
        
        f = io.StringIO(csv_content)
        reader = csv.DictReader(f, fieldnames=['name', 'description', 'price'])
        
        for row in reader:
            # Basic validation that price is a float
            float(row['price'])
            Ware.objects.create(
                merchant=merchant,
                name=row['name'],
                description=row['description'],
                price=float(row['price'])
            )
        
        return JsonResponse({'message': 'Wares uploaded successfully'}, status=200)
    except Exception:
        return JsonResponse({'error': 'Invalid CSV format'}, status=400)

def list_wares(request):
    merchant = get_authenticated_merchant(request)
    if not merchant:
        return JsonResponse({'error': 'Unauthorized'}, status=401)
    
    min_price = request.GET.get('minPrice')
    max_price = request.GET.get('maxPrice')
    
    wares = Ware.objects.all()
    
    if min_price:
        try:
            wares = wares.filter(price__gte=float(min_price))
        except ValueError:
            pass
    if max_price:
        try:
            wares = wares.filter(price__lte=float(max_price))
        except ValueError:
            pass
            
    # Render as HTML table
    html = '<table border="1"><tr><th>Name</th><th>Price</th><th>Description</th><th>Merchant Email</th></tr>'
    for w in wares:
        html += f'<tr><td>{w.name}</td><td>{w.price}</td><td>{w.description}</td><td>{w.merchant.email}</td></tr>'
    html += '</table>'
    
    return HttpResponse(html, content_type='text/html')