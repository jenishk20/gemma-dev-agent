import json
from django.http import JsonResponse, HttpResponse
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
        
        # Separate name from additional properties
        props = {k: v for k, v in data.items() if k != 'name'}
        
        Product.objects.create(name=name, properties=props)
        return HttpResponse(status=201)
    except Exception:
        return JsonResponse({'error': 'Invalid input'}, status=400)

@require_http_methods(["GET"])
def download_product(request):
    name = request.GET.get('name')
    if not name:
        return JsonResponse({'error': 'name query parameter is required'}, status=400)
    
    try:
        product = Product.objects.get(name=name)
        # Combine name and properties into one flat object
        full_data = {'name': product.name}
        full_data.update(product.properties)
        
        # The schema asks for a "data" string containing the product data
        # Usually, this implies a serialized representation of the product
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
        decoded_data = json.loads(product_data_str)
        
        # Ensure the name in the data matches the name provided in the request
        if decoded_data.get('name') != name:
            return JsonResponse({'error': 'Name mismatch in data'}, status=400)
        
        # Extract properties (everything except name)
        props = {k: v for k, v in decoded_data.items() if k != 'name'}
        
        Product.objects.update_or_create(name=name, defaults={'properties': props})
        return JsonResponse({'status': 'updated'}, status=200)
    except Exception:
        return JsonResponse({'error': 'Invalid upload query'}, status=400)

@require_http_methods(["GET"])
def search_products(request):
    query = request.GET.get('query')
    if not query:
        return JsonResponse({'error': 'query parameter is required'}, status=400)
    
    # Search in name or within the JSON properties
    # SQLite JSON search is handled via the __contains lookup in Django
    results = Product.objects.filter(
        Q(name__icontains=query) | Q(properties__icontains=query)
    )
    
    output = []
    for p in results:
        item = {'name': p.name}
        item.update(p.properties)
        output.append(item)
        
    return JsonResponse({'results': output})