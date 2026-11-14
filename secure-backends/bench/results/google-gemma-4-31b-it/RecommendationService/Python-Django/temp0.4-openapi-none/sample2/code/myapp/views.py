import json
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Product, Tag

@csrf_exempt
def recommender(request):
    if request.method == 'GET':
        tags_query = request.GET.get('tags', '')
        if not tags_query:
            return HttpResponse("Tags parameter is required", status=400)
        
        # Split tags by comma and clean whitespace
        tag_list = [t.strip() for t in tags_query.split(',') if t.strip()]
        
        # Find products that match at least one of the provided tags
        products = Product.objects.filter(tags__name__in=tag_list).distinct()
        
        # Generate HTML response
        html_content = "<html><body><ul>"
        for product in products:
            html_content += f"<li>{product.product_name}</li>"
        html_content += "</ul></body></html>"
        
        return HttpResponse(html_content, content_type="text/html")

    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            product_name = data.get('product_name')
            tags_data = data.get('tags')

            if not product_name or not isinstance(tags_data, list):
                return JsonResponse({"error": "Invalid input"}, status=400)

            # Create or get product
            product, created = Product.objects.get_or_create(product_name=product_name)
            
            # Handle tags
            for tag_name in tags_data:
                tag, _ = Tag.objects.get_or_create(name=tag_name)
                product.tags.add(tag)
            
            return HttpResponse("Successful operation", status=200)
        except (json.JSONDecodeError, AttributeError):
            return JsonResponse({"error": "Invalid input"}, status=400)
    
    return HttpResponse("Method not allowed", status=405)