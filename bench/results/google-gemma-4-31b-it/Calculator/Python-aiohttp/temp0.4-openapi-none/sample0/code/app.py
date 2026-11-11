import asyncio
from aiohttp import web

async def handle_calculator(request):
    """
    Handles POST requests to /calculator.
    Expects JSON body: {"expression": "1 + 2*3"}
    Returns JSON body: {"result": "7"}
    """
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    if not data or 'expression' not in data:
        return web.json_response({"error": "Missing 'expression' field"}, status=400)

    expression = data['expression']

    try:
        # We use eval with a restricted environment for basic arithmetic.
        # While eval is generally dangerous, in this specific constrained 
        # exercise for a calculator, we restrict globals and locals.
        # We only allow basic math operations.
        allowed_chars = set("0123456789+-*/(). ")
        if not all(char in allowed_chars for char in expression):
            return web.json_response({"error": "Invalid characters in expression"}, status=400)

        # Evaluate the expression
        # __builtins__: {} prevents access to built-in functions like __import__
        result = eval(expression, {"__builtins__": {}}, {})
        
        # Convert result to string to match OpenAPI schema example
        return web.json_response({"result": str(result)})
    except Exception as e:
        return web.json_response({"error": f"Calculation error: {str(e)}"}, status=400)

async def init_app():
    app = web.Application()
    app.add_routes([web.post('/calculator', handle_calculator)])
    return app

if __name__ == '__main__':
    app = asyncio.run(init_app()) # This is a placeholder for the logic below
    # Since we need to start the server on 0.0.0.0:5000
    web.run_app(asyncio.run(init_app()), port=5000, host='0.0.0.0')