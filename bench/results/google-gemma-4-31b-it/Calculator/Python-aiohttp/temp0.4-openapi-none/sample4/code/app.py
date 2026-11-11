import asyncio
from aiohttp import web

async def calculate_handler(request):
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

    expression = data.get('expression')

    # Security Note: eval() is used here to satisfy the requirement of a general 
    # arithmetic expression calculator. In a production environment, 
    # a proper parser or a restricted environment should be used.
    try:
        # We restrict the globals and locals to prevent access to built-ins
        # and only allow basic math operations.
        allowed_names = {"__builtins__": {}}
        # eval can be dangerous; for a simple calculator we use a basic approach.
        # We strip characters that aren't digits, operators, or whitespace.
        safe_chars = "0123456789+-*/(). "
        if not all(char in safe_chars for char in expression):
            raise ValueError("Invalid characters in expression")
            
        result = eval(expression, allowed_names, {})
        # Convert result to string as per OpenAPI schema example
        return web.json_response({"result": str(result)})
    except Exception as e:
        return web.json_response({"error": f"Invalid input: {str(e)}"}, status=400)

async def init_app():
    app = web.Application()
    app.add_routes([web.post('/calculator', calculate_handler)])
    return app

if __name__ == '__main__':
    app = asyncio.run(init_app()) # This is a helper, but we need to run the server
    # Re-initializing for the runner
    app = web.Application()
    app.add_routes([web.post('/calculator', calculate_handler)])
    web.run_app(app, host='0.0.0.0', port=5000)