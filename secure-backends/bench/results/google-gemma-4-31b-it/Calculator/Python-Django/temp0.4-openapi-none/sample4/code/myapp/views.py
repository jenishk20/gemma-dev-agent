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
        
        # Basic security check: only allow numbers, operators, and spaces
        # to prevent arbitrary code execution via eval()
        allowed_chars = "0123456789+-*/(). "
        if not all(char in allowed_chars for char in expression):
            return JsonResponse({'error': 'Invalid characters in expression'}, status=400)
        
        # Evaluate the expression
        # eval is used here as a simple calculator implementation given the constraints
        result = eval(expression, {"__builtins__": {}}, {})
        
        # Convert result to string as per OpenAPI schema example
        return JsonResponse({'result': str(result)}, status=200)
        
    except (json.JSONDecodeError, SyntaxError, ZeroDivisionError, TypeError):
        return JsonResponse({'error': 'Invalid input'}, status=400)
    except Exception:
        return JsonResponse({'error': 'Internal server error'}, status=500)