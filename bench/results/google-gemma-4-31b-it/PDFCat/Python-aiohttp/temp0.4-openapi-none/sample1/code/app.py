import asyncio
import os
import tempfile
import uuid
from aiohttp import web

async def concatenate_pdfs(request):
    """
    Handles the /concatenate endpoint.
    Expects multipart/form-data with a 'files' field containing multiple PDF files.
    """
    try:
        # Parse multipart data
        data = await request.post()
        files = data.get('files')

        if not files or not isinstance(files, list) or len(files) == 0:
            return web.json_response({"error": "Invalid input or missing files."}, status=400)

        # Create a temporary directory to store uploaded files and the result
        with tempfile.TemporaryDirectory() as tmpdir:
            input_paths = []
            
            # Save uploaded files to disk
            for i, file_field in enumerate(files):
                # aiohttp MultiDict values for files are FileStorage objects
                filename = f"input_{i}.pdf"
                filepath = os.path.join(tmpdir, filename)
                
                # Read the content of the uploaded file
                content = await file_field.read()
                with open(filepath, 'wb') as f:
                    f.write(content)
                input_paths.append(filepath)

            # Define output path
            output_filename = f"result_{uuid.uuid4()}.pdf"
            output_path = os.path.join(tmpdir, output_filename)

            # Construct the pdfunite command
            # pdfunite [input1] [input2] ... [output]
            cmd = ['pdfunite'] + input_paths + [output_path]

            # Run the CLI command asynchronously
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                return web.json_response({"error": f"An error occurred while processing the files: {stderr.decode()}"}, status=500)

            # Read the resulting PDF
            with open(output_path, 'rb') as f:
                pdf_content = f.read()

            return web.Response(body=pdf_content, content_type='application/pdf')

    except Exception as e:
        return web.json_response({"error": f"Internal Server Error: {str(e)}"}, status=500)

async def init_app():
    app = web.Application()
    app.router.add_post('/concatenate', concatenate_pdfs)
    return app

if __name__ == '__main__':
    app = asyncio.run(init_app()) # This is a conceptual wrapper, aiohttp.web.run_app is standard
    # Re-implementing standard run_app logic for clarity
    import aiohttp.web
    web.run_app(asyncio.run(init_app()), port=5000, address='0.0.0.0')

# Correction: The above logic for run_app is slightly off in the wrapper. 
# Let's use the standard aiohttp entry point.
def run():
    app = web.Application()
    app.router.add_post('/concatenate', concatenate_pdfs)
    web.run_app(app, port=5000, address='0.0.0.0')

if __name__ == '__main__':
    run()