import asyncio
from aiohttp import web

async def calculate_handler(request):
    """
    Handles the POST /calculator endpoint.
    Expects a JSON body with an 'expression' key.
    """
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    if not data or 'expression' not in data:
        return web.json_response({"error": "Missing 'expression' field"}, status=400)

    expression = data['expression']

    try:
        # We use eval() here for a simple calculator implementation.
        # To mitigate security risks in a real production environment, 
        # one should use a proper expression parser or a restricted environment.
        # We restrict globals and locals to prevent access to built-ins.
        allowed_names = {"__builtins__": {}}
        # Basic sanitization: only allow digits, operators, spaces, and parentheses
        # This prevents the execution of arbitrary Python code.
        sanitized_expression = ""
        for char in expression:
            if char in "0123456789+-*/(). ":
                sanitized_expression += char
            else:
                return web.json_response({"error": "Invalid characters in expression"}, status=400)

        result = eval(sanitized_expression, allowed_names, {})
        return web.json_response({"result": str(result)})
    except Exception as e:
        return web.json_response({"error": f"Calculation error: {str(e)}"}, status=400)

async def init_app():
    app = web.Application()
    app.add_routes([web.post('/calculator', calculate_handler)])
    return app

if __name__ == '__main__':
    app = asyncio.run(init_app()) # This is a placeholder, we use web.run_app
    # Re-initializing for the standard run_app flow
    app = web.Application()
    app.add_routes([web.post('/calculator', calculate_handler)])
    web.run_app(app, host='0.0.0.0', port=5000)