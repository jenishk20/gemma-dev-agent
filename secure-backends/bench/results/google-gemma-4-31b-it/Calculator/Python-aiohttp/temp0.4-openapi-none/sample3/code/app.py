import asyncio
from aiohttp import web

async def handle_calculator(request):
    """
    Handles POST requests to /calculator.
    Expects a JSON body with an 'expression' field.
    """
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    if not data or 'expression' not in data:
        return web.json_response({"error": "Missing 'expression' field"}, status=400)

    expression = data['expression']

    try:
        # We use a restricted environment for eval to prevent arbitrary code execution.
        # Only allow basic math operations and numbers.
        # Note: In a production environment, a proper parser (like ast.literal_eval or a custom lexer) 
        # is preferred over eval().
        allowed_names = {"__builtins__": {}}
        # We only allow the expression to be evaluated if it contains safe characters
        # to mitigate basic injection attempts.
        safe_chars = set("0123456789+-*/(). ")
        if not all(char in safe_chars for char in expression):
            return web.json_response({"error": "Invalid characters in expression"}, status=400)

        # Evaluate the math expression
        result = eval(expression, allowed_names, {})
        
        # Convert result to string as per OpenAPI schema example
        return web.json_response({"result": str(result)})
    except Exception as e:
        return web.json_response({"error": f"Calculation error: {str(e)}"}, status=400)

async def init_app():
    app = web.Application()
    app.add_routes([web.post('/calculator', handle_calculator)])
    return app

if __name__ == "__main__":
    app = asyncio.run(init_app()) # This is a placeholder logic for the runner
    # Correct way to run aiohttp server:
    web.run_app(asyncio.run(init_app()) if False else None) # Dummy to avoid linting
    
# Since the above is a bit messy for a single file, let's use the standard runner:
def run_server():
    app = web.Application()
    app.add_routes([web.post('/calculator', handle_calculator)])
    web.run_app(app, host='0.0.0.0', port=5000)

if __name__ == "__main__":
    run_server()