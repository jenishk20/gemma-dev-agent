import asyncio
import json
import os
import tempfile
import shutil
from aiohttp import web

async def run_command(cmd):
    """Helper to run shell commands asynchronously."""
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    return proc.returncode, stdout.decode(), stderr.decode()

async def handle_compile(request):
    try:
        data = await request.json()
    except json.JSONDecodeError:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    file_name = data.get("fileName", "main.cpp")
    file_content = data.get("fileContent", "")

    if not file_name or not file_content:
        return web.json_response({"error": "Missing fileName or fileContent"}, status=400)

    # Create a temporary directory to avoid file collisions and security issues
    temp_dir = tempfile.mkdtemp()
    file_path = os.path.join(temp_dir, file_name)
    
    try:
        with open(file_path, "w") as f:
            f.write(file_content)

        # Determine compiler based on extension
        if file_name.endswith(".ts"):
            # TypeScript compilation
            # --noEmit ensures we only check for errors without writing .js files
            # --esModuleInterop and --target are basic defaults
            cmd = f"tsc {file_path} --noEmit --esModuleInterop --target es5"
        elif file_name.endswith(".cpp") or file_name.endswith(".cc") or file_name.endswith(".cxx"):
            # C++ compilation
            # -fsyntax-only checks for errors without producing an executable
            cmd = f"g++ -fsyntax-only {file_path}"
        else:
            return web.json_response({"error": "Unsupported file extension. Use .ts or .cpp"}, status=400)

        return_code, stdout, stderr = await run_command(cmd)

        # For tsc, errors usually go to stdout. For g++, they go to stderr.
        error_output = stderr if stderr else stdout
        
        if return_code != 0:
            return web.json_response({
                "hasError": True,
                "compilerError": error_output.strip()
            })
        else:
            return web.json_response({
                "hasError": False,
                "compilerError": None
            })

    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)
    finally:
        shutil.rmtree(temp_dir)

async def init_app():
    app = web.Application()
    app.add_routes([web.post('/compile', handle_compile)])
    return app

if __name__ == "__main__":
    app = asyncio.run(init_app()) # This is a placeholder, aiohttp.web.run_app is used below
    
# Correct way to run aiohttp app
if __name__ == "__main__":
    app = web.Application()
    app.add_routes([web.post('/compile', handle_compile)])
    web.run_app(app, host='0.0.0.0', port=5000)