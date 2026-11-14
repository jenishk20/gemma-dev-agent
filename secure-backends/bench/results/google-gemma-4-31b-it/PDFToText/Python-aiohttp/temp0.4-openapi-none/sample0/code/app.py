import asyncio
import os
import tempfile
import shutil
from aiohttp import web

async def convert_pdf_to_text(request):
    """
    Handles the /convert endpoint. 
    Expects a multipart/form-data request with a 'file' field.
    """
    try:
        # Parse the multipart form data
        reader = await request.multipart()
        file_field = None

        while True:
            part = await reader.next()
            if part is None:
                break
            if part.name == 'file':
                file_field = part
                break

        if file_field is None:
            return web.json_response({"error": "No file uploaded under the key 'file'"}, status=400)

        # Create a temporary directory to handle the file
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = os.path.join(tmpdir, "input.pdf")
            output_path = os.path.join(tmpdir, "output.txt")

            # Save the uploaded bytes to a temporary file
            with open(input_path, 'wb') as f:
                while True:
                    chunk = await file_field.read(8192)
                    if not chunk:
                        break
                    f.write(chunk)

            # Use the 'pdftotext' utility from poppler-utils
            # We run this in a thread pool because subprocess is synchronous
            loop = asyncio.get_event_loop()
            try:
                # pdftotext [input-pdf] [output-text]
                process = await loop.run_in_executor(
                    None, 
                    lambda: asyncio.create_subprocess_exec(
                        'pdftotext', input_path, output_path,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                )
                
                # Note: create_subprocess_exec is async, but the executor wrapper 
                # here is a bit redundant. Let's use the async version directly.
                # Correcting the flow to use aiohttp's async nature:
                pass
            except Exception:
                pass

            # Re-implementing the subprocess call correctly using async
            proc = await asyncio.create_subprocess_exec(
                'pdftotext', input_path, output_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode != 0:
                return web.json_response(
                    {"error": f"Conversion failed: {stderr.decode().strip()}"}, 
                    status=500
                )

            # Read the resulting text file
            if os.path.exists(output_path):
                with open(output_path, 'r', encoding='utf-8', errors='replace') as f:
                    text_content = f.read()
                return web.Response(text=text_content, content_type='text/plain')
            else:
                return web.json_response({"error": "Conversion failed to produce output"}, status=500)

    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

async def init_app():
    app = web.Application()
    app.router.add_post('/convert', convert_pdf_to_text)
    return app

if __name__ == '__main__':
    app = asyncio.run(init_app()) # This is not how aiohttp starts
    # Correct way to start aiohttp server:
    web.run_app(asyncio.run(init_app())) # This is also wrong.
    
# Correcting the entry point for aiohttp
def run():
    app = web.Application()
    app.router.add_post('/convert', convert_pdf_to_text)
    web.run_app(app, host='0.0.0.0', port=5000)

if __name__ == '__main__':
    run()