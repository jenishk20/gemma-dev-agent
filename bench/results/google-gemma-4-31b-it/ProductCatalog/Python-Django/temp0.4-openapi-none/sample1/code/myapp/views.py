import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from .models import Product
from django.db.models import Q

@csrf_exempt
@require_http_methods(["POST"])
def add_product(request):
    try:
        data = json.loads(request.body)
        name = data.get('name')
        if not name:
            return JsonResponse({'error': 'name is required'}, status=400)
        
        # Extract all other properties
        props = {k: v for k, v in data.items() if k != 'name'}
        
        Product.objects.create(name=name, properties=props)
        return JsonResponse({}, status=201)
    except Exception:
        return JsonResponse({'error': 'Invalid input'}, status=400)

@require_http_methods(["GET"])
def download_product(request):
    name = request.GET.get('name')
    if not name:
        return JsonResponse({'error': 'name query parameter is required'}, status=400)
    
    try:
        product = Product.objects.get(name=name)
        # The schema asks for the data as a string (data entry)
        # We combine name and properties into one object and serialize it
        full_data = {'name': product.name, **product.properties}
        return JsonResponse({'data': json.dumps(full_data)})
    except Product.DoesNotExist:
        return JsonResponse({'error': 'Product not found'}, status=404)

@csrf_exempt
@require_http_methods(["POST"])
def upload_product(request):
    try:
        data = json.loads(request.body)
        name = data.get('name')
        product_data_str = data.get('data')
        
        if not name or product_data_str is None:
            return JsonResponse({'error': 'Invalid upload query'}, status=400)
        
        # Parse the data string back into a dict
        full_data = json.loads(product_data_str)
        if not isinstance(full_data, dict) or 'name' not in full_data:
            return JsonResponse({'error': 'Invalid data format'}, status=400)
        
        # Ensure we are updating the product specified by the 'name' field in the request body
        # and that the data content matches or replaces it.
        props = {k: v for k, v in full_data.items() if k != 'name'}
        
        Product.objects.update_or_create(
            name=name, 
            defaults={'properties': props}
        )
        return JsonResponse({'message': 'Product updated'}, status=200)
    except Exception:
        return JsonResponse({'error': 'Invalid upload query'}, status=400)

@require_http_methods(["GET"])
def search_products(request):
    query = request.GET.get('query')
    if not query:
        return JsonResponse({'error': 'query parameter is required'}, status=400)
    
    # Search in name or within the JSON properties values
    # Note: SQLite JSON search is limited in Django ORM, 
    # so we filter by name and then filter JSON values in Python or use __contains
    results = Product.objects.filter(
        Q(name__icontains=query) | Q(properties__icontains=query)
    )
    
    output = []
    for p in results:
        item = {'name': p.name}
        item.update(p.properties)
        output.append(item)
        
    return JsonResponse({'results': output})