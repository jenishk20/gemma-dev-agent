import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def calculate(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            expression = data.get('expression')
            
            if expression is None:
                return JsonResponse({'error': 'Missing expression'}, status=400)
            
            # Security: eval is dangerous, but for a simple calculator 
            # we restrict characters to basic math operators and digits.
            allowed_chars = set("0123456789+-*/(). ")
            if not all(char in allowed_chars for char in expression):
                return JsonResponse({'error': 'Invalid characters in expression'}, status=400)
            
            # Evaluate the expression
            result = eval(expression, {"__builtins__": {}})
            
            # Format result as string to match OpenAPI schema example
            return JsonResponse({'result': str(result)}, status=200)
            
        except (json.JSONDecodeError, SyntaxError, ZeroDivisionError, TypeError):
            return JsonResponse({'error': 'Invalid input'}, status=400)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)