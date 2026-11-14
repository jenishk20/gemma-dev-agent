import json
from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from .models import Product, Tag
from django.db.models import Q

@csrf_exempt
def recommender(request):
    if request.method == 'GET':
        tags_query = request.GET.get('tags')
        if not tags_query:
            return HttpResponseBadRequest("Missing tags parameter")
        
        search_tags = [t.strip() for t in tags_query.split(',') if t.strip()]
        if not search_tags:
            return HttpResponseBadRequest("No valid tags provided")

        # Find products that match at least one of the provided tags
        products = Product.objects.filter(tags__name__in=search_tags).distinct()
        
        # Generate HTML response
        html_output = "<ul>"
        for product in products:
            html_output += f"<li>{product.product_name}</li>"
        html_output += "</ul>"
        
        if not products:
            html_output = "No products found matching the tags."
            
        return HttpResponse(html_output, content_type="text/html")

    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            product_name = data.get('product_name')
            tags_list = data.get('tags')

            if not product_name or not isinstance(tags_list, list):
                return HttpResponseBadRequest("Invalid input: product_name and tags (list) are required")

            # Create product
            product, created = Product.objects.get_or_create(product_name=product_name)
            
            # Create tags
            for tag_name in tags_list:
                Tag.objects.get_or_create(name=tag_name, defaults={'product': product})
            
            return HttpResponse("Successful operation", status=200)
        except (json.JSONDecodeError, TypeError):
            return HttpResponseBadRequest("Invalid JSON input")

    return HttpResponse("Method Not Allowed", status=405)