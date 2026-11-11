import io
import zipfile
from aiohttp import web

async def convert_zip_to_txt(request):
    """
    Handles the POST /convert endpoint.
    Expects a multipart/form-data request with a 'file' field containing a zip archive.
    """
    try:
        # Parse the multipart form data
        data = await request.post()
        file_field = data.get('file')

        if not file_field:
            return web.response.Response(text="Missing 'file' field in request", status=400)

        # file_field is a FileStorage object. Read the binary content.
        zip_bytes = await file_field.read()
        
        # Use io.BytesIO to treat the bytes as a file-like object for zipfile
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
            # Get list of all files in the zip
            file_list = z.namelist()
            
            concatenated_text = []
            
            for file_name in file_list:
                # We only process files (ignore directories)
                if not file_name.endswith('/'):
                    try:
                        # Read the content of the file
                        with z.open(file_name) as f:
                            # Attempt to decode as utf-8, ignoring errors for non-text files
                            content = f.read().decode('utf-8', errors='ignore')
                            concatenated_text.append(content)
                    except Exception:
                        # If a file cannot be read, we skip it
                        continue
            
            # Join all contents with a newline separator
            result = "\n".join(concatenated_text)
            
            return web.Response(text=result, content_type='text/plain')

    except Exception as e:
        return web.Response(text=f"Invalid input or processing error: {str(e)}", status=400)

async def init_app():
    app = web.Application()
    app.add_routes([web.post('/convert', convert_zip_to_txt)])
    return app

if __name__ == '__main__':
    app = web.Application()
    app.add_routes([web.post('/convert', convert_zip_to_txt)])
    web.run_app(app, host='0.0.0.0', port=5000)