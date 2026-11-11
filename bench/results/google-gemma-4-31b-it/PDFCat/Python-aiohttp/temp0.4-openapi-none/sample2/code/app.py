import asyncio
import os
import tempfile
import shutil
from aiohttp import web

async def concatenate_pdfs(request):
    """
    Handler to concatenate multiple PDF files using pdfunite CLI.
    """
    try:
        # Extract files from multipart/form-data
        reader = await request.multipart()
        pdf_files = []
        
        field = await reader.next()
        if field is None:
            return web.json_response({"error": "No files provided"}, status=400)

        # We expect a field named 'files' containing multiple files
        # aiohttp's multipart reader iterates through all parts.
        # We will collect all files uploaded in the request.
        
        # Create a temporary directory to store uploaded files
        with tempfile.TemporaryDirectory() as tmpdir:
            current_field = field
            while current_field:
                if current_field.name == 'files':
                    # Create a unique filename for each uploaded PDF
                    filename = f"file_{len(pdf_files)}.pdf"
                    filepath = os.path.join(tmpdir, filename)
                    
                    with open(filepath, 'wb') as f:
                        while True:
                            chunk = await current_field.read_chunk()
                            if not chunk:
                                break
                            f.write(chunk)
                    pdf_files.append(filepath)
                
                current_field = await reader.next()

            if not pdf_files:
                return web.json_response({"error": "Invalid input or missing files."}, status=400)

            # Output path for the concatenated PDF
            output_path = os.path.join(tmpdir, "concatenated.pdf")
            
            # Construct the pdfunite command: pdfunite input1.pdf input2.pdf ... output.pdf
            # We use asyncio.create_subprocess_exec to avoid blocking the event loop
            cmd = ['pdfunite'] + pdf_files + [output_path]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                return web.json_response({"error": f"pdfunite error: {stderr.decode()}"}, status=500)

            # Read the resulting PDF and return it
            if os.path.exists(output_path):
                with open(output_path, 'rb') as f:
                    data = f.read()
                return web.Response(body=data, content_type='application/pdf')
            else:
                return web.json_response({"error": "Concatenation failed, output file not found."}, status=500)

    except Exception as e:
        return web.json_response({"error": f"An error occurred while processing the files: {str(e)}"}, status=500)

async def init_app():
    app = web.Application()
    app.router.add_post('/concatenate', concatenate_pdfs)
    return app

if __name__ == '__main__':
    app = asyncio.run(init_app()) # This is a helper, but we need to run the app
    # Since init_app is async, we handle it differently for aiohttp.web.run_app
    
# Correcting the entry point for aiohttp
def run():
    app = web.Application()
    app.router.add_post('/concatenate', concatenate_pdfs)
    web.run_app(app, host='0.0.0.0', port=5000)

if __name__ == '__main__':
    run()