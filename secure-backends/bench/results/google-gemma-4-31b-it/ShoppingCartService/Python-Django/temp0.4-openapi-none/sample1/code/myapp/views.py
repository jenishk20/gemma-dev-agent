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
            return JsonResponse({'error': 'Missing required fields'}, status=400)
        
        try:
            cart = Cart.objects.get(id=cart_id)
        except Cart.DoesNotExist:
            return JsonResponse({'error': 'Cart not found'}, status=404)
        
        cart_item, created = CartItem.objects.get_or_create(cart=cart, item_id=item_id)
        new_count = cart_item.count + count
        
        if new_count <= 0:
            cart_item.delete()
        else:
            cart_item.count = new_count
            cart_item.save()
            
        return JsonResponse({'status': 'success'}, status=200)
    except (json.JSONDecodeError, TypeError):
        return JsonResponse({'error': 'Invalid request'}, status=400)

@csrf_exempt
def retrieve_cart(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        cart_id = data.get('cart_id')
        
        if not cart_id:
            return JsonResponse({'error': 'Missing cart_id'}, status=400)
        
        try:
            cart = Cart.objects.get(id=cart_id)
        except Cart.DoesNotExist:
            return JsonResponse({'error': 'Cart not found'}, status=404)
        
        items = CartItem.objects.filter(cart=cart)
        items_list = [{'item_id': item.item_id, 'count': item.count} for item in items]
        
        return JsonResponse({'items': items_list}, status=200)
    except (json.JSONDecodeError, TypeError):
        return JsonResponse({'error': 'Invalid request'}, status=400)