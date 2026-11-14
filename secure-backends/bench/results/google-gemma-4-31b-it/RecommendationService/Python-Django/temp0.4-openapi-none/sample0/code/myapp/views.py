import json
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
from .models import Product, Tag, ProductTag

@csrf_exempt
def recommender(request):
    if request.method == 'GET':
        tags_query = request.GET.get('tags', '')
        if not tags_query:
            return HttpResponse("Missing tags parameter", status=400)
        
        search_tags = [t.strip() for t in tags_query.split(',') if t.strip()]
        
        # Find products that have at least one of the tags
        products = Product.objects.filter(
            product_tags__tag__name__in=search_tags
        ).distinct()
        
        # Generate HTML response
        html_content = "<html><body><h1>Recommended Products</h1><ul>"
        for product in products:
            html_content += f"<li>{product.product_name}</li>"
        html_content += "</ul></body></html>"
        
        return HttpResponse(html_content, content_type="text/html")

    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            product_name = data.get('product_name')
            tags_list = data.get('tags')
            
            if not product_name or not isinstance(tags_list, list):
                return HttpResponse("Invalid input", status=400)
            
            # Create product
            product, created = Product.objects.get_or_create(product_name=product_name)
            
            # Create tags and link them
            for tag_name in tags_list:
                tag, _ = Tag.objects.get_or_create(name=tag_name)
                ProductTag.objects.get_or_create(product=product, tag=tag)
                
            return HttpResponse("Successful operation", status=200)
        except Exception:
            return HttpResponse("Invalid input", status=400)

    return HttpResponse("Method Not Allowed", status=405)