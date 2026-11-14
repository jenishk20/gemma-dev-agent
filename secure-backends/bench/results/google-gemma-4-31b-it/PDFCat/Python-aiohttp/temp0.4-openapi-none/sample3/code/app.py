import asyncio
import os
import tempfile
import uuid
from aiohttp import web

async def concatenate_pdfs(request):
    """
    Handler for the /concatenate endpoint.
    Expects multipart/form-data with a field 'files' containing multiple PDF files.
    """
    try:
        # Parse multipart data
        reader = await request.multipart()
        
        input_files = []
        # Create a temporary directory to store uploaded chunks
        with tempfile.TemporaryDirectory() as temp_dir:
            field = await reader.next()
            
            # The schema specifies 'files' as an array of binary strings.
            # In aiohttp multipart, multiple files under the same name 
            # are handled by iterating through the multipart reader.
            
            # We need to find the 'files' field. Since multiple files can be uploaded,
            # we iterate through all fields.
            
            # Reset reader to start if necessary, but aiohttp reader is a stream.
            # We'll collect all files named 'files'.
            
            # Since we already called .next() once, we handle the first field then loop.
            current_field = field
            while current_field is not None:
                if current_field.name == 'files':
                    # Create a unique filename for each uploaded part
                    file_ext = '.pdf'
                    filename = f"{uuid.uuid4()}{file_ext}"
                    filepath = os.path.join(temp_dir, filename)
                    
                    with open(filepath, 'wb') as f:
                        while True:
                            chunk = await current_field.read_chunk()
                            if not chunk:
                                break
                            f.write(chunk)
                    
                    input_files.append(filepath)
                
                current_field = await reader.next()

            if not input_files:
                return web.json_response({"error": "Invalid input or missing files."}, status=400)

            # Path for the output concatenated file
            output_filename = f"result_{uuid.uuid4()}.pdf"
            output_path = os.path.join(temp_dir, output_filename)

            # Construct the pdfunite command: pdfunite file1.pdf file2.pdf ... output.pdf
            # Using asyncio.create_subprocess_exec to avoid blocking the event loop
            cmd = ['pdfunite'] + input_files + [output_path]
            
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
                    data = f.read()
                return web.Response(body=data, content_type='application/pdf')
            else:
                return web.json_response({"error": "Concatenation failed to produce a file."}, status=500)

    except Exception as e:
        return web.json_response({"error": f"Internal Server Error: {str(e)}"}, status=500)

async def init_app():
    app = web.Application()
    app.router.add_post('/concatenate', concatenate_pdfs)
    return app

if __name__ == '__main__':
    app = asyncio.run(init_app()) # This is a conceptual wrapper; aiohttp uses web.run_app
    # To strictly follow the requirement of starting the server on 0.0.0.0:5000:
    # We use the standard web.run_app pattern.
    
# Re-structuring to ensure it runs correctly via web.run_app
def run_server():
    app = web.Application()
    app.router.add_post('/concatenate', concatenate_pdfs)
    web.run_app(app, host='0.0.0.0', port=5000)

if __name__ == '__main__':
    # The previous block was a sketch, this is the actual execution
    app = web.Application()
    app.router.add_post('/concatenate', concatenate_pdfs)
    web.run_app(app, host='0.0.0.0', port=5000)