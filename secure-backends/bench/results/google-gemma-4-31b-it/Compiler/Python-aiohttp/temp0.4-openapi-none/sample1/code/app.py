import asyncio
import json
import os
import tempfile
import subprocess
from aiohttp import web

async def run_compiler(filename, content):
    """
    Handles the logic of writing the file to a temporary directory,
    running the appropriate compiler, and capturing the output.
    """
    # Create a temporary directory to avoid collisions and cleanup
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, filename)
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        try:
            if filename.endswith(".ts"):
                # TypeScript compilation: tsc
                # We use --noEmit to just check for errors without generating js files
                process = await asyncio.create_subprocess_exec(
                    "tsc", file_path, "--noEmit",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
            elif filename.endswith(".cpp") or filename.endswith(".cc") or filename.endswith(".cxx"):
                # C++ compilation: g++
                # -fsyntax-only checks for compilation errors without producing an executable
                process = await asyncio.create_subprocess_exec(
                    "g++", "-fsyntax-only", file_path,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
            else:
                return {"hasError": True, "compilerError": "Unsupported file extension. Please use .ts or .cpp"}

            stdout, stderr = await process.communicate()
            
            # For tsc, errors often go to stdout. For g++, they go to stderr.
            output = (stdout or b"") + (stderr or b"")
            decoded_output = output.decode("utf-8").strip()

            if process.returncode != 0:
                return {
                    "hasError": True,
                    "compilerError": decoded_output if decoded_output else "Unknown compilation error"
                }
            else:
                return {
                    "hasError": False,
                    "compilerError": None
                }

        except Exception as e:
            return {"hasError": True, "compilerError": str(e)}

async def handle_compile(request):
    """
    POST /compile handler
    """
    try:
        data = await request.json()
    except json.JSONDecodeError:
        return web.json_response({"error": "Invalid JSON body"}, status=400)

    file_name = data.get("fileName")
    file_content = data.get("fileContent")

    if not file_name or file_content is None:
        return web.json_response({"error": "Missing fileName or fileContent"}, status=400)

    result = await run_compiler(file_name, file_content)
    return web.json_response(result)

async def init_app():
    app = web.Application()
    app.add_routes([web.post('/compile', handle_compile)])
    return app

if __name__ == "__main__":
    app = asyncio.run(init_app()) # This is a placeholder logic, aiohttp.web.run_app is standard
    # Since we need to start the server on 0.0.0.0:5000
    web.run_app(asyncio.run(init_app()), port=5000, address="0.0.0.0")

# Correcting the entry point for aiohttp
def start_server():
    app = web.Application()
    app.add_routes([web.post('/compile', handle_compile)])
    web.run_app(app, port=5000, address="0.0.0.0")

if __name__ == "__main__":
    start_server()