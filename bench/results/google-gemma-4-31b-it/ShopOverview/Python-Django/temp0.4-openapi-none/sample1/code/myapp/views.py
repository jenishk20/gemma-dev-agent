import csv
import io
import json
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render
from .models import Merchant, Ware

@csrf_exempt
def register_merchant(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            email = data.get('email')
            name = data.get('name')
            password = data.get('password')
            
            if not all([email, name, password]):
                return JsonResponse({'error': 'Missing fields'}, status=400)
            
            Merchant.objects.create(email=email, name=name, password=password)
            return HttpResponse(status=201)
        except Exception:
            return JsonResponse({'error': 'Invalid input'}, status=400)
    return HttpResponse(status=405)

@csrf_exempt
def login_merchant(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            email = data.get('email')
            password = data.get('password')
            
            merchant = Merchant.objects.filter(email=email, password=password).first()
            if merchant:
                request.session['merchant_id'] = merchant.id
                return JsonResponse('Login successful', status=200)
            else:
                return JsonResponse({'error': 'Invalid email or password'}, status=401)
        except Exception:
            return JsonResponse({'error': 'Invalid input'}, status=400)
    return HttpResponse(status=405)

@csrf_exempt
def upload_wares(request):
    if request.method == 'POST':
        merchant_id = request.session.get('merchant_id')
        if not merchant_id:
            return HttpResponse(status=401)
        
        try:
            data = json.loads(request.body)
            csv_content = data.get('csv', '')
            f = io.StringIO(csv_content)
            reader = csv.reader(f)
            
            merchant = Merchant.objects.get(pk=merchant_id)
            for row in reader:
                if len(row) != 3:
                    continue
                name, description, price = row
                Ware.objects.create(name=name, description=description, price=float(price), merchant=merchant)
            
            return HttpResponse(status=200)
        except Exception:
            return HttpResponse(status=400)
    return HttpResponse(status=405)

def list_wares(request):
    merchant_id = request.session.get('merchant_id')
    if not merchant_id:
        return HttpResponse(status=401)
    
    min_price = request.GET.get('minPrice')
    max_price = request.GET.get('maxPrice')
    
    wares = Ware.objects.all()
    
    if min_price:
        wares = wares.filter(price__gte=float(min_price))
    if max_price:
        wares = wares.filter(price__lte=float(max_price))
        
    # Render as HTML table
    html = "<table><tr><th>Name</th><th>Price</th><th>Description</th><th>Merchant</th></tr>"
    for w in wares:
        html += f"<tr><td>{w.name}</td><td>{w.price}</td><td>{w.description}</td><td>{w.merchant.email}</td></tr>"
    html += "</table>"
    
    return HttpResponse(html, content_type="text/html")