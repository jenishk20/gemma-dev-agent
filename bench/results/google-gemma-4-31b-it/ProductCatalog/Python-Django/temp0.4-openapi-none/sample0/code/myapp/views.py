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
        
        # Extract additional properties
        props = {k: v for k, v in data.items() if k != 'name'}
        
        Product.objects.create(name=name, properties=props)
        return JsonResponse({}, status=201)
    except Exception:
        return JsonResponse({'error': 'Invalid input'}, status=400)

@require_http_methods(["GET"])
def download_product(request):
    name = request.GET.get('name')
    if not name:
        return JsonResponse({'error': 'name is required'}, status=400)
    
    try:
        product = Product.objects.get(name=name)
        # The OpenAPI schema implies the "data" field is a string representation 
        # of the product's unstructured properties.
        data_str = json.dumps(product.properties)
        return JsonResponse({'data': data_str})
    except Product.DoesNotExist:
        return JsonResponse({'error': 'Product not found'}, status=404)

@csrf_exempt
@require_http_methods(["POST"])
def upload_product(request):
    try:
        data = json.loads(request.body)
        name = data.get('name')
        product_data = data.get('data')
        
        if not name or product_data is None:
            return JsonResponse({'error': 'Invalid upload query'}, status=400)
        
        # Parse the data string back into a dict
        props = json.loads(product_data)
        if not isinstance(props, dict):
            return JsonResponse({'error': 'Data must be a JSON object string'}, status=400)
            
        Product.objects.update_or_create(name=name, defaults={'properties': props})
        return JsonResponse({'message': 'Product updated'}, status=200)
    except Exception:
        return JsonResponse({'error': 'Invalid upload query'}, status=400)

@require_http_methods(["GET"])
def search_products(request):
    query = request.GET.get('query')
    if not query:
        return JsonResponse({'error': 'query is required'}, status=400)
    
    # Search in name or within the JSON properties
    # SQLite supports JSON querying via Django's JSONField
    results = Product.objects.filter(
        Q(name__icontains=query) | Q(properties__icontains=query)
    )
    
    output = []
    for p in results:
        item = {'name': p.name}
        item.update(p.properties)
        output.append(item)
        
    return JsonResponse({'results': output})