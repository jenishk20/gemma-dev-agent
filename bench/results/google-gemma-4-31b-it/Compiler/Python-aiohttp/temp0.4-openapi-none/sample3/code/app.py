import asyncio
import os
import tempfile
import shutil
from aiohttp import web

async def run_compiler(filename, content):
    """
    Handles the logic of writing the file to a temporary directory,
    running the appropriate compiler, and capturing the output.
    """
    # Create a temporary directory to avoid filename collisions and pollution
    temp_dir = tempfile.mkdtemp()
    try:
        file_path = os.path.join(temp_dir, filename)
        with open(file_path, 'w') as f:
            f.write(content)

        if filename.endswith('.ts'):
            # TypeScript compilation
            # We use 'tsc' from the global npm install. 
            # --noEmit prevents generating .js files, we just want the type check/compile errors.
            cmd = f"tsc {file_path} --noEmit"
        elif filename.endswith('.cpp'):
            # C++ compilation
            # -fsyntax-only checks for errors without producing an executable
            cmd = f"g++ -fsyntax-only {file_path}"
        else:
            return True, "Unsupported file extension. Please use .ts or .cpp"

        # Run the process
        process = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        # Most compilers return non-zero exit code on error
        if process.returncode != 0:
            # Combine stderr and stdout as different compilers output errors to different streams
            error_msg = (stderr + stdout).decode('utf-8').strip()
            return False, error_msg if error_msg else "Compilation failed without specific error output."
        
        return True, None

    except Exception as e:
        return False, str(e)
    finally:
        shutil.rmtree(temp_dir)

async def handle_compile(request):
    """
    POST /compile handler
    """
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON body"}, status=400)

    file_name = data.get('fileName')
    file_content = data.get('fileContent')

    if not file_name or file_content is None:
        return web.json_response({"error": "Missing fileName or fileContent"}, status=400)

    success, error_msg = await run_compiler(file_name, file_content)

    # The schema expects hasError: true if compilation failed
    return web.json_response({
        "hasError": not success,
        "compilerError": error_msg if not success else None
    })

async def init_app():
    app = web.Application()
    app.add_routes([web.post('/compile', handle_compile)])
    return app

if __name__ == '__main__':
    app = asyncio.run(init_app())
    web.run_app(app, host='0.0.0.0', port=5000)