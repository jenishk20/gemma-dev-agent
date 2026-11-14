import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views import View
from .models import Product
from django.db.models import Q

@csrf_exempt
class ProductAPIView(View):
    def post(self, request, path):
        # Handle /add and /upload
        if path == 'add':
            try:
                data = json.loads(request.body)
                name = data.get('name')
                if not name:
                    return JsonResponse({'error': 'Name is required'}, status=400)
                
                # Extract all other fields as unstructured properties
                props = {k: v for k, v in data.items() if k != 'name'}
                
                Product.objects.create(name=name, properties=props)
                return JsonResponse({'status': 'created'}, status=201)
            except Exception:
                return JsonResponse({'error': 'Invalid input'}, status=400)

        elif path == 'upload':
            try:
                data = json.loads(request.body)
                name = data.get('name')
                payload_data = data.get('data')
                
                if not name or payload_data is None:
                    return JsonResponse({'error': 'Invalid upload query'}, status=400)
                
                # The schema says data is a string. We assume it's a JSON string 
                # representing the properties or a serialized version of the product.
                # Since /download returns a JSON object, we parse it.
                try:
                    props_dict = json.loads(payload_data)
                except json.JSONDecodeError:
                    # If it's just a raw string, we store it as a value in a generic key or handle as is
                    props_dict = {"data": payload_data}

                # Remove name from properties if it exists to avoid duplication
                if isinstance(props_dict, dict) and 'name' in props_dict:
                    del props_dict['name']

                Product.objects.update_or_create(name=name, defaults={'properties': props_dict})
                return JsonResponse({'status': 'updated'}, status=200)
            except Exception:
                return JsonResponse({'error': 'Invalid upload query'}, status=400)

    def get(self, request, path):
        if path == 'download':
            name = request.GET.get('name')
            if not name:
                return JsonResponse({'error': 'Name is required'}, status=400)
            
            try:
                product = Product.objects.get(name=name)
                # Combine name and properties into one object, then stringify for the 'data' field
                full_data = {'name': product.name}
                full_data.update(product.properties)
                return JsonResponse({'data': json.dumps(full_data)})
            except Product.DoesNotExist:
                return JsonResponse({'error': 'Product not found'}, status=404)

        elif path == 'search':
            query = request.GET.get('query')
            if not query:
                return JsonResponse({'error': 'Query is required'}, status=400)
            
            # Search in name or within the JSON properties
            # SQLite JSON search is handled via __contains or custom filters in Django
            results = Product.objects.filter(
                Q(name__icontains=query) | Q(properties__icontains=query)
            )
            
            output = []
            for p in results:
                item = {'name': p.name}
                item.update(p.properties)
                output.append(item)
                
            return JsonResponse({'results': output}, status=200)

# Helper to route paths without trailing slashes
def api_router(request):
    path = request.path_info.strip('/')
    view = ProductAPIView.as_view()
    return view(request, path)