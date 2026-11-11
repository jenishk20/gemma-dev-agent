import csv
import io
import json
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render
from .models import Merchant, Ware

def get_authenticated_merchant(request):
    # The OpenAPI specifies cookieAuth with name AUTH_COOKIE
    # We store the merchant_id in the cookie for this simple implementation
    auth_cookie = request.COOKIES.get('AUTH_COOKIE')
    if auth_cookie:
        try:
            return Merchant.objects.get(id=int(auth_cookie))
        except (Merchant.DoesNotExist, ValueError):
            return None
    return None

@csrf_exempt
def register_merchant(request):
    if request.method != 'POST':
        return HttpResponse(status=405)
    
    try:
        data = json.loads(request.body)
        email = data['email']
        name = data['name']
        password = data['password']
        
        if Merchant.objects.filter(email=email).exists():
            return HttpResponse(status=400)
            
        Merchant.objects.create(email=email, name=name, password=password)
        return HttpResponse(status=201)
    except (KeyError, json.JSONDecodeError):
        return HttpResponse(status=400)

@csrf_exempt
def login_merchant(request):
    if request.method != 'POST':
        return HttpResponse(status=405)
    
    try:
        data = json.loads(request.body)
        email = data['email']
        password = data['password']
        
        merchant = Merchant.objects.filter(email=email, password=password).first()
        if merchant:
            response = JsonResponse("Login successful", safe=False)
            response.set_cookie('AUTH_COOKIE', str(merchant.id))
            return response
        else:
            return JsonResponse({'error': 'Invalid email or password'}, status=401)
    except (KeyError, json.JSONDecodeError):
        return HttpResponse(status=400)

@csrf_exempt
def upload_wares(request):
    if request.method != 'POST':
        return HttpResponse(status=405)
    
    merchant = get_authenticated_merchant(request)
    if not merchant:
        return HttpResponse(status=401)
    
    try:
        data = json.loads(request.body)
        csv_data = data.get('csv', '')
        
        f = io.StringIO(csv_data)
        reader = csv.reader(f)
        
        for row in reader:
            if not row: continue
            if len(row) != 3:
                return HttpResponse(status=400)
            
            name, description, price_str = row
            Ware.objects.create(
                merchant=merchant,
                name=name,
                description=description,
                price=float(price_str)
            )
        return HttpResponse(status=200)
    except (ValueError, json.JSONDecodeError):
        return HttpResponse(status=400)

def list_wares(request):
    merchant = get_authenticated_merchant(request)
    if not merchant:
        return HttpResponse(status=401)
    
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
    html = "<table><thead><tr><th>Name</th><th>Price</th><th>Description</th><th>Merchant</th></tr></thead><tbody>"
    for w in wares:
        html += f"<tr><td>{w.name}</td><td>{w.price}</td><td>{w.description}</td><td>{w.merchant.email}</td></tr>"
    html += "</tbody></table>"
    
    return HttpResponse(html, content_type="text/html")