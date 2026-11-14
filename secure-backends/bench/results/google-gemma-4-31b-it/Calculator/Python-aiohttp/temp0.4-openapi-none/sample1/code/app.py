import asyncio
from aiohttp import web

async def calculate(request):
    """
    Handles POST requests to /calculator.
    Expects a JSON body with an 'expression' field.
    """
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    expression = data.get("expression")
    if expression is None or not isinstance(expression, str):
        return web.json_response({"error": "Missing or invalid expression"}, status=400)

    try:
        # We use a restricted set of globals for eval to mitigate basic security risks,
        # although in a production environment, a proper parser (like ast.literal_eval 
        # or a custom math parser) is recommended.
        # The schema requires a string result.
        result = eval(expression, {"__builtins__": {}}, {})
        return web.json_response({"result": str(result)})
    except Exception as e:
        return web.json_response({"error": f"Invalid input: {str(e)}"}, status=400)

async def init_app():
    app = web.Application()
    app.add_routes([web.post('/calculator', calculate)])
    return app

if __name__ == "__main__":
    app = asyncio.run(init_app()) # This is a helper logic, but aiohttp.web.run_app is standard
    # To ensure it runs on 0.0.0.0:5000 as requested:
    web.run_app(app, host='0.0.0.0', port=5000)