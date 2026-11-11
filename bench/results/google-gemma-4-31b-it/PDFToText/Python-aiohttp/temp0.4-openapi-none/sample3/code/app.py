import asyncio
import os
import tempfile
import shutil
from aiohttp import web

async def convert_pdf_to_text(request):
    """
    Handles the POST /convert endpoint.
    Expects a multipart/form-data request with a 'file' field.
    """
    try:
        # Read the multipart form data
        reader = await request.multipart()
        if reader is None:
            return web.json_response({"error": "Invalid multipart request"}, status=400)

        pdf_file = None
        # Iterate through the fields to find the 'file' upload
        while True:
            part = await reader.next()
            if part is None:
                break
            if part.name == 'file':
                pdf_file = part
                break

        if not pdf_file:
            return web.json_response({"error": "Missing 'file' field in request"}, status=400)

        # Create a temporary directory to handle the file
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = os.path.join(tmpdir, "input.pdf")
            output_path = os.path.join(tmpdir, "output.txt")

            # Save the uploaded bytes to a temporary file
            with open(input_path, 'wb') as f:
                while True:
                    chunk = await pdf_file.read_chunk()
                    if not chunk:
                        break
                    f.write(chunk)

            # Use the 'pdftotext' utility from poppler-utils
            # We use asyncio.create_subprocess_exec to avoid blocking the event loop
            process = await asyncio.create_subprocess_exec(
                'pdftotext', input_path, output_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                error_msg = stderr.decode().strip() or "Unknown error during conversion"
                return web.json_response({"error": f"Conversion failed: {error_msg}"}, status=500)

            # Read the resulting text file
            if os.path.exists(output_path):
                with open(output_path, 'r', encoding='utf-8', errors='replace') as f:
                    text_content = f.read()
                return web.Response(text=text_content, content_type='text/plain')
            else:
                return web.json_response({"error": "Conversion succeeded but no output file was created"}, status=500)

    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

async def init_app():
    app = web.Application()
    app.router.add_post('/convert', convert_pdf_to_text)
    return app

if __name__ == '__main__':
    app = asyncio.run(init_app()) # This is a helper logic, but aiohttp.web.run_app is standard
    # Re-implementing the standard run_app logic for clarity
    import asyncio
    from aiohttp import web
    
    # Correct way to run aiohttp app
    async def start_server():
        app = web.Application()
        app.router.add_post('/convert', convert_pdf_to_text)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', 5000)
        await site.start()
        print("Server started at http://0.0.0.0:5000")
        await asyncio.Event().wait()

    try:
        asyncio.run(start_server())
    except KeyboardInterrupt:
        pass