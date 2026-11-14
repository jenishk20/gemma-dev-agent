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
            return JsonResponse({'error': 'Name is required'}, status=400)
        
        # Extract additional properties
        properties = {k: v for k, v in data.items() if k != 'name'}
        
        Product.objects.create(name=name, properties=properties)
        return JsonResponse({'status': 'Product successfully added'}, status=201)
    except Exception:
        return JsonResponse({'error': 'Invalid input'}, status=400)

@require_http_methods(["GET"])
def download_product(request):
    name = request.GET.get('name')
    if not name:
        return JsonResponse({'error': 'Name is required'}, status=400)
    
    try:
        product = Product.objects.get(name=name)
        # The schema asks for the "data of a product" as a string. 
        # We will serialize the full object (name + properties) into a JSON string.
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
        
        # Parse the data string back into a dictionary
        product_dict = json.loads(product_data_str)
        
        # The name in the data string should ideally match the name provided
        # but the prompt says "fully replaces any previous data".
        # We update the name and the properties.
        updated_name = product_dict.get('name', name)
        properties = {k: v for k, v in product_dict.items() if k != 'name'}
        
        Product.objects.update_or_create(
            name=updated_name, 
            defaults={'properties': properties}
        )
        
        return JsonResponse({'status': 'The product with the given name was updated.'}, status=200)
    except Exception:
        return JsonResponse({'error': 'Invalid upload query'}, status=400)

@require_http_methods(["GET"])
def search_products(request):
    query = request.GET.get('query')
    if not query:
        return JsonResponse({'error': 'Invalid search query'}, status=400)
    
    # Search in name OR within the JSON properties values
    # SQLite JSON search is handled by Django's __contains or custom lookups
    # For simplicity and compatibility, we filter name and then filter properties in Python 
    # or use the JSON field's ability to search values.
    results = Product.objects.filter(
        Q(name__icontains=query) | Q(properties__icontains=query)
    )
    
    output = []
    for p in results:
        item = {'name': p.name}
        item.update(p.properties)
        output.append(item)
        
    return JsonResponse({'results': output}, status=200)