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
        
        # Using a restricted set of characters for safety to avoid arbitrary code execution
        # Only allow digits, operators, spaces, and parentheses
        allowed_chars = set("0123456789+-*/.() ")
        if not all(char in allowed_chars for char in expression):
            return JsonResponse({'error': 'Invalid characters in expression'}, status=400)
            
        # eval is used here as the requirement is a simple calculator and 
        # the input is strictly filtered above.
        result = eval(expression, {"__builtins__": None}, {})
        
        # Convert result to string to match OpenAPI schema example
        return JsonResponse({'result': str(result)}, status=200)
        
    except (ValueError, SyntaxError, ZeroDivisionError, TypeError):
        return JsonResponse({'error': 'Invalid input'}, status=400)
    except Exception:
        return JsonResponse({'error': 'Internal server error'}, status=500)