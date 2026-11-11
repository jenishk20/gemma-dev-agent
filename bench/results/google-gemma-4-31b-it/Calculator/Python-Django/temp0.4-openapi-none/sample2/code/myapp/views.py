import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def calculate(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        expression = data.get('expression')
        
        if expression is None:
            return JsonResponse({'error': 'Missing expression'}, status=400)
        
        # Using eval safely by restricting globals and locals
        # In a production environment, a proper math parser should be used.
        # We restrict the environment to prevent arbitrary code execution.
        allowed_names = {"__builtins__": {}}
        result = eval(expression, allowed_names, {})
        
        return JsonResponse({'result': str(result)}, status=200)
    except Exception:
        return JsonResponse({'error': 'Invalid input'}, status=400)