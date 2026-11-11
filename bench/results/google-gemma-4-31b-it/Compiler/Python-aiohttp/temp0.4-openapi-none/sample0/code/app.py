import asyncio
import json
import os
import tempfile
import shutil
from aiohttp import web

# Configuration
PORT = 5000
HOST = '0.0.0.0'

async def run_command(cmd, cwd=None):
    """Helper to run shell commands asynchronously."""
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd
    )
    stdout, stderr = await proc.communicate()
    return proc.returncode, stdout.decode(), stderr.decode()

async def handle_compile(request):
    try:
        data = await request.json()
    except json.JSONDecodeError:
        return web.json_response({'error': 'Invalid JSON'}, status=400)

    file_name = data.get('fileName')
    file_content = data.get('fileContent')

    if not file_name or file_content is None:
        return web.json_response({'error': 'Missing fileName or fileContent'}, status=400)

    # Create a temporary directory to avoid file collisions and pollution
    temp_dir = tempfile.mkdtemp()
    try:
        file_path = os.path.join(temp_dir, file_name)
        with open(file_path, 'w') as f:
            f.write(file_content)

        has_error = False
        compiler_error = None

        if file_name.endswith('.ts'):
            # Compile TypeScript using tsc
            # --noEmit ensures we just check for errors without writing .js files
            cmd = f"tsc {file_name} --noEmit --esModuleInterop"
            ret, stdout, stderr = await run_command(cmd, cwd=temp_dir)
            
            # tsc outputs errors to stdout
            if ret != 0 or stdout.strip():
                has_error = True
                compiler_error = stdout.strip() or stderr.strip()

        elif file_name.endswith('.cpp'):
            # Compile C++ using g++
            # -fsyntax-only checks for compilation errors without producing an executable
            cmd = f"g++ -fsyntax-only {file_name}"
            ret, stdout, stderr = await run_command(cmd, cwd=temp_dir)
            
            if ret != 0:
                has_error = True
                compiler_error = stderr.strip() or stdout.strip()
        else:
            return web.json_response({'error': 'Unsupported file extension. Use .ts or .cpp'}, status=400)

        return web.json_response({
            'hasError': has_error,
            'compilerError': compiler_error
        })

    except Exception as e:
        return web.json_response({'error': str(e)}, status=500)
    finally:
        shutil.rmtree(temp_dir)

async def init_app():
    app = web.Application()
    app.add_routes([web.post('/compile', handle_compile)])
    return app

if __name__ == '__main__':
    app = asyncio.run(init_app()) # This is a simplification; usually we use web.run_app
    # Using web.run_app for the actual server start
    web.run_app(app, host=HOST, port=PORT)

# Since the above logic has a slight mismatch in how web.run_app is called 
# with the async init, let's rewrite the entry point cleanly.
def start():
    app = web.Application()
    app.add_routes([web.post('/compile', handle_compile)])
    web.run_app(app, host=HOST, port=PORT)

if __name__ == '__main__':
    start()