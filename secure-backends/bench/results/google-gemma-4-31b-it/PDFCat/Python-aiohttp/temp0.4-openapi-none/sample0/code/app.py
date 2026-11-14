import os
import asyncio
import tempfile
import shutil
from aiohttp import web

async def concatenate_pdfs(request):
    """
    Handles the /concatenate endpoint.
    Expects multipart/form-data with a field 'files' containing PDFs.
    """
    try:
        # Parse multipart data
        data = await request.post()
        files = data.get('files')

        if not files:
            return web.json_response({"error": "Invalid input or missing files."}, status=400)

        # Ensure files is a list (aiohttp handles multiple files with same name as a list)
        if not isinstance(files, list):
            files = [files]

        if len(files) == 0:
            return web.json_response({"error": "Invalid input or missing files."}, status=400)

        # Create a temporary directory to store input and output files
        with tempfile.TemporaryDirectory() as tmpdir:
            input_paths = []
            
            # Save uploaded files to disk
            for i, file_field in enumerate(files):
                # Check if it's actually a file upload
                if not hasattr(file_field, 'filename'):
                    return web.json_response({"error": "Invalid input or missing files."}, status=400)
                
                filename = f"input_{i}.pdf"
                filepath = os.path.join(tmpdir, filename)
                
                with open(filepath, 'wb') as f:
                    # Read the file content from the MultiReaderField
                    content = await file_field.read()
                    f.write(content)
                
                input_paths.append(filepath)

            output_path = os.path.join(tmpdir, "output.pdf")
            
            # Construct the pdfunite command
            # pdfunite file1.pdf file2.pdf ... output.pdf
            cmd = ['pdfunite'] + input_paths + [output_path]
            
            # Run the CLI tool asynchronously
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                return web.json_response({"error": "An error occurred while processing the files."}, status=500)

            # Read the resulting PDF and return it
            if os.path.exists(output_path):
                with open(output_path, 'rb') as f:
                    pdf_data = f.read()
                return web.Response(body=pdf_data, content_type='application/pdf')
            else:
                return web.json_response({"error": "An error occurred while processing the files."}, status=500)

    except Exception as e:
        return web.json_response({"error": f"An error occurred while processing the files: {str(e)}"}, status=500)

async def init_app():
    app = web.Application()
    app.router.add_post('/concatenate', concatenate_pdfs)
    return app

if __name__ == '__main__':
    app = asyncio.run(init_app()) # This is a placeholder logic for the runner
    # aiohttp.web.run_app is the standard way to start the server
    web.run_app(asyncio.run(init_app()), port=5000, address='0.0.0.0')

# Correcting the entry point for aiohttp
def run_server():
    app = web.Application()
    app.router.add_post('/concatenate', concatenate_pdfs)
    web.run_app(app, port=5000, address='0.0.0.0')

if __name__ == '__main__':
    run_server()