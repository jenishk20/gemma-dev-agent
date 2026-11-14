import asyncio
import os
import tempfile
import shutil
from aiohttp import web

async def run_command(cmd):
    """Helper to run shell commands asynchronously."""
    process = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    return process.returncode, stdout.decode(), stderr.decode()

async def handle_compile(request):
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    file_name = data.get("fileName")
    file_content = data.get("fileContent")

    if not file_name or not file_content:
        return web.json_response({"error": "Missing fileName or fileContent"}, status=400)

    # Create a temporary directory to avoid collisions and cleanup
    temp_dir = tempfile.mkdtemp()
    file_path = os.path.join(temp_dir, file_name)
    
    try:
        with open(file_path, "w") as f:
            f.write(file_content)

        # Determine compiler based on file extension
        if file_name.endswith(".ts"):
            # TypeScript compiler: tsc
            # We use --noEmit to just check for errors without generating JS files
            cmd = f"tsc {file_path} --noEmit --esModuleInterop"
        elif file_name.endswith(".cpp") or file_name.endswith(".cc") or file_name.endswith(".cxx"):
            # C++ compiler: g++
            # We compile to an object file to check for syntax/type errors
            cmd = f"g++ -c {file_path} -o {file_path}.o"
        else:
            return web.json_response({"error": "Unsupported file extension. Use .ts or .cpp"}, status=400)

        return_code, stdout, stderr = await run_command(cmd)

        # For tsc, errors often go to stdout or stderr depending on version/config
        # For g++, errors go to stderr
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
    app = asyncio.run(init_app()) # This is a placeholder logic for the runner
    # Since we need to start the server on 0.0.0.0:5000
    web.run_app(asyncio.run(init_app()), port=5000, address='0.0.0.0')

# Correcting the run logic for aiohttp
def main():
    app = web.Application()
    app.add_routes([web.post('/compile', handle_compile)])
    web.run_app(app, port=5000, address='0.0.0.0')

if __name__ == "__main__":
    main()