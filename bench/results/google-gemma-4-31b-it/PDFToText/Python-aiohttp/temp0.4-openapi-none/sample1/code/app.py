import asyncio
import os
import tempfile
import shutil
from aiohttp import web

async def convert_pdf_to_text(file_path):
    """
    Uses the pdftotext utility from poppler-utils to extract text.
    pdftotext <input_pdf> - outputs to stdout.
    """
    process = await asyncio.create_subprocess_exec(
        'pdftotext', file_path, '-',
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    
    if process.returncode != 0:
        raise Exception(f"pdftotext failed: {stderr.decode()}")
    
    return stdout.decode('utf-8')

async def handle_convert(request):
    """
    Handles the POST /convert endpoint.
    Expects a multipart/form-data request with a 'file' field.
    """
    reader = await request.multipart()
    field = None
    
    # Iterate through the multipart fields to find the 'file' field
    while True:
        field = await reader.next()
        if field is None:
            break
        if field.name == 'file':
            break

    if not field:
        return web.json_response({'error': 'No file uploaded. Please provide a "file" field.'}, status=400)

    # Create a temporary directory to store the uploaded PDF
    temp_dir = tempfile.mkdtemp()
    try:
        file_path = os.path.join(temp_dir, 'input.pdf')
        
        # Save the uploaded content to a temporary file
        with open(file_path, 'wb') as f:
            while True:
                chunk = await field.read_chunk()
                if not chunk:
                    break
                f.write(chunk)

        # Extract text using the utility
        text_content = await convert_pdf_to_text(file_path)
        
        # Return the result as plain text
        return web.Response(text=text_content, content_type='text/plain')

    except Exception as e:
        print(f"Error during conversion: {e}")
        return web.json_response({'error': str(e)}, status=500)
    finally:
        # Clean up the temporary directory
        shutil.rmtree(temp_dir, ignore_errors=True)

async def init_app():
    app = web.Application()
    app.router.add_post('/convert', handle_convert)
    return app

if __name__ == '__main__':
    app = asyncio.run(init_app()) # This is a helper logic, but aiohttp.web.run_app is standard
    # Re-initializing for proper run_app call
    async def start():
        app = await init_app()
        web.run_app(app, host='0.0.0.0', port=5000)

    # Standard aiohttp entry point
    app = web.Application()
    app.router.add_post('/convert', handle_convert)
    web.run_app(app, host='0.0.0.0', port=5000)