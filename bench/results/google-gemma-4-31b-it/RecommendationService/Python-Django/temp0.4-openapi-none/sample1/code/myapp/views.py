import json
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
from .models import Product, Tag

@csrf_exempt
def recommender(request):
    if request.method == 'GET':
        tags_query = request.GET.get('tags', '')
        if not tags_query:
            return HttpResponse("Missing tags parameter", status=400)
        
        tag_list = [t.strip() for t in tags_query.split(',') if t.strip()]
        
        # Find products that match at least one of the provided tags
        products = Product.objects.filter(tags__name__in=tag_list).distinct()
        
        html_response = "<ul>"
        for product in products:
            html_response += f"<li>{product.product_name}</li>"
        html_response += "</ul>"
        
        if not products:
            html_response = "No products found matching the tags."
            
        return HttpResponse(html_response, content_type="text/html")

    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            product_name = data.get('product_name')
            tags = data.get('tags')

            if not product_name or not isinstance(tags, list):
                return HttpResponse("Invalid input", status=400)

            product = Product.objects.create(product_name=product_name)
            for tag_name in tags:
                Tag.objects.create(name=tag_name, product=product)

            return HttpResponse("Successful operation", status=200)
        except (json.JSONDecodeError, Exception):
            return HttpResponse("Invalid input", status=400)

    return HttpResponse("Method not allowed", status=405)