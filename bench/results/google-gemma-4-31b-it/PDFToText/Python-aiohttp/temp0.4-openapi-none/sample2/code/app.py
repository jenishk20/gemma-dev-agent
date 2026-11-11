import asyncio
import os
import tempfile
import shutil
from aiohttp import web

async def convert_pdf_to_text(file_path):
    """
    Uses the pdftotext utility from poppler-utils to extract text.
    Since pdftotext is a CLI tool, we run it using asyncio.create_subprocess_exec.
    """
    # pdftotext outputs to stdout if no output file is specified, 
    # but it's more reliable to specify a target or capture stdout.
    # Command: pdftotext -layout <input_pdf> -
    process = await asyncio.create_subprocess_exec(
        'pdftotext', '-layout', file_path, '-',
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()

    if process.returncode != 0:
        raise Exception(f"pdftotext error: {stderr.decode().strip()}")

    return stdout.decode('utf-8')

async def handle_convert(request):
    """
    Handles the POST /convert endpoint.
    Expects multipart/form-data with a 'file' field.
    """
    try:
        reader = await request.multipart()
        if reader is None:
            return web.json_response({"error": "Request must be multipart/form-data"}, status=400)

        pdf_file = None
        # Iterate through the fields to find the 'file' part
        while True:
            field = await reader.next()
            if field is None:
                break
            if field.name == 'file':
                pdf_file = field
                break

        if pdf_file is None:
            return web.json_response({"error": "Missing 'file' field in request"}, status=400)

        # Create a temporary directory to store the uploaded PDF
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = os.path.join(tmpdir, "input.pdf")
            
            # Save the uploaded file to disk
            with open(input_path, 'wb') as f:
                while True:
                    chunk = await pdf_file.read_chunk()
                    if not chunk:
                        break
                    f.write(chunk)

            # Extract text using the utility
            text_content = await convert_pdf_to_text(input_path)
            
            # Return as plain text as per OpenAPI spec
            return web.Response(text=text_content, content_type='text/plain')

    except Exception as e:
        # Log the error for the server admin and return 500
        print(f"Error processing PDF: {e}")
        return web.json_response({"error": str(e)}, status=500)

async def init_app():
    app = web.Application()
    app.add_routes([web.post('/convert', handle_convert)])
    return app

if __name__ == '__main__':
    app = asyncio.run(init_app()) # This is just a placeholder, we need the runner
    # Correct way to start aiohttp server
    async def main():
        app = await init_app()
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', 5000)
        print("Server started at http://0.0.0.0:5000")
        await site.start()
        # Keep the server running
        await asyncio.Event().wait()

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass