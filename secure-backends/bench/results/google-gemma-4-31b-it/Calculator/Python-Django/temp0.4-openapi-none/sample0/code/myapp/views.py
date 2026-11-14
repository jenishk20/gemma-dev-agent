import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views import View

@csrf_exempt
class CalculatorView(View):
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            expression = data.get('expression')
            
            if expression is None:
                return JsonResponse({'error': 'Missing expression'}, status=400)
            
            # Use a restricted set of characters to prevent arbitrary code execution
            # Only allow digits, operators, spaces, and parentheses
            allowed_chars = set("0123456789+-*/(). ")
            if not all(char in allowed_chars for char in expression):
                return JsonResponse({'error': 'Invalid characters in expression'}, status=400)
            
            # eval is used here for simplicity as per the "simple math" requirement, 
            # but we've added a basic character whitelist for safety.
            result = eval(expression)
            
            # Convert result to string as per OpenAPI schema example "7"
            return JsonResponse({'result': str(result)})
            
        except Exception:
            return JsonResponse({'error': 'Invalid input'}, status=400)

# Instantiate the view for urls.py
calculator_view = CalculatorView.as_view()