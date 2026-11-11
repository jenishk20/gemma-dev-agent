import asyncio
import os
import tempfile
import uuid
from aiohttp import web

async def concatenate_pdfs(request):
    """
    Handles the /concatenate endpoint.
    Expects multipart/form-data with a field named 'files'.
    """
    try:
        # Parse multipart data
        reader = await request.multipart()
        
        pdf_files = []
        # Create a temporary directory to store uploaded PDFs for pdfunite
        with tempfile.TemporaryDirectory() as tmpdir:
            while True:
                part = await reader.next()
                if part is None:
                    break
                
                if part.name == 'files':
                    # Generate a unique filename to avoid collisions
                    filename = f"{uuid.uuid4()}.pdf"
                    filepath = os.path.join(tmpdir, filename)
                    
                    # Read the stream and write to disk
                    with open(filepath, 'wb') as f:
                        while True:
                            chunk = await part.read_chunk()
                            if not chunk:
                                break
                            f.write(chunk)
                    
                    pdf_files.append(filepath)

            if not pdf_files:
                return web.json_response({"error": "Invalid input or missing files."}, status=400)

            # Define output path
            output_filename = "concatenated.pdf"
            output_path = os.path.join(tmpdir, output_filename)

            # Construct the pdfunite command
            # pdfunite file1.pdf file2.pdf ... output.pdf
            cmd = ["pdfunite"] + pdf_files + [output_path]

            # Run the CLI command asynchronously
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                return web.json_response({"error": f"An error occurred while processing the files: {stderr.decode()}"}, status=500)

            # Read the resulting PDF and return it
            with open(output_path, 'rb') as f:
                content = f.read()

            return web.Response(body=content, content_type='application/pdf')

    except Exception as e:
        return web.json_response({"error": f"Internal Server Error: {str(e)}"}, status=500)

async def init_app():
    app = web.Application()
    app.router.add_post('/concatenate', concatenate_pdfs)
    return app

if __name__ == "__main__":
    app = asyncio.run(init_app()) # This is a placeholder logic for the runner
    # Correct way to run aiohttp app
    web.run_app(asyncio.run(init_app()), port=5000, address='0.0.0.0')