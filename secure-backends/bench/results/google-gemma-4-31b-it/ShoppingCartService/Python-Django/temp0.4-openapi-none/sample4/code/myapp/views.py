import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Cart, CartItem

@csrf_exempt
def create_cart(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    cart = Cart.objects.create()
    return JsonResponse({'cart_id': str(cart.id)}, status=201)

@csrf_exempt
def add_to_cart(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        cart_id = data.get('cart_id')
        item_id = data.get('item_id')
        count = data.get('count')

        if cart_id is None or item_id is None or count is None:
            return JsonResponse({'error': 'Invalid request'}, status=400)

        try:
            cart = Cart.objects.get(id=cart_id)
        except (Cart.DoesNotExist, ValueError):
            return JsonResponse({'error': 'Cart not found'}, status=404)

        item, created = CartItem.objects.get_or_create(cart=cart, item_id=item_id)
        
        new_count = item.count + count
        if new_count <= 0:
            item.delete()
        else:
            item.count = new_count
            item.save()

        return JsonResponse({'status': 'success'}, status=200)
    except Exception:
        return JsonResponse({'error': 'Invalid request'}, status=400)

@csrf_exempt
def retrieve_cart(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        cart_id = data.get('cart_id')

        if not cart_id:
            return JsonResponse({'error': 'Invalid request'}, status=400)

        try:
            cart = Cart.objects.get(id=cart_id)
        except (Cart.DoesNotExist, ValueError):
            return JsonResponse({'error': 'Cart not found'}, status=404)

        items = CartItem.objects.filter(cart=cart)
        result = {
            'items': [{'item_id': i.item_id, 'count': i.count} for i in items]
        }
        return JsonResponse(result, status=200)
    except Exception:
        return JsonResponse({'error': 'Invalid request'}, status=400)