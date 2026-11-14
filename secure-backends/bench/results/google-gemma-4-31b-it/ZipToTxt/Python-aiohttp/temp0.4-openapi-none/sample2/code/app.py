import io
import zipfile
from aiohttp import web

async def convert_zip_to_txt(request):
    """
    Handles the POST /convert endpoint.
    Expects a multipart/form-data request with a 'file' field.
    """
    try:
        # Read the multipart form data
        data = await request.post()
        
        # Extract the file from the form data
        file_field = data.get('file')
        if not file_field:
            return web.Response(text="Missing 'file' field in request", status=400)

        # Read the binary content of the uploaded file
        # file_field is a FileField object; we read its content
        zip_content = await file_field.read()
        
        # Use io.BytesIO to treat the bytes as a file-like object for zipfile
        with zipfile.ZipFile(io.BytesIO(zip_content)) as z:
            # Get a list of all files in the zip
            file_list = z.namelist()
            
            combined_text = []
            for filename in file_list:
                # We only process files that are not directories
                # and we attempt to read them as text.
                # Note: zipfile.open returns a binary stream.
                try:
                    with z.open(filename) as f:
                        # Read bytes and decode to utf-8, ignoring errors for non-text files
                        content = f.read().decode('utf-8', errors='ignore')
                        # Only append if the content is not empty or if it's a valid text file
                        # To strictly follow "contents of all text files", we append everything
                        # that can be decoded.
                        combined_text.append(content)
                except Exception:
                    # Skip files that cannot be opened
                    continue
            
            # Join all contents with a newline separator
            final_result = "\n".join(combined_text)
            
        return web.Response(text=final_result, content_type='text/plain')

    except Exception as e:
        return web.Response(text=f"Invalid input or processing error: {str(e)}", status=400)

async def init_app():
    app = web.Application()
    app.router.add_post('/convert', convert_zip_to_txt)
    return app

if __name__ == "__main__":
    app = init_app()
    # Start the server on 0.0.0.0:5000
    web.run_app(app, host='0.0.0.0', port=5000)