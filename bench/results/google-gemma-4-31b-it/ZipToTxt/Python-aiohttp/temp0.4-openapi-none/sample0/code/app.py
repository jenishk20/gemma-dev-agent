import io
import zipfile
from aiohttp import web

async def convert_zip_to_txt(request):
    """
    Handler to convert a uploaded zip file into a single concatenated text string.
    """
    try:
        # Parse multipart form data
        data = await request.post()
        
        if 'file' not in data:
            return web.response.text("Missing 'file' field in request", status=400)
        
        file_field = data['file']
        # file_field is a FileStorage object
        filename = file_field.filename
        content = file_field.file.read()

        if not content:
            return web.response.text("Empty file uploaded", status=400)

        # Use io.BytesIO to treat the bytes as a file-like object for zipfile
        with zipfile.ZipFile(io.BytesIO(content)) as z:
            all_text = []
            # Iterate through all files in the zip
            for name in z.namelist():
                # Skip directories
                if name.endswith('/'):
                    continue
                
                try:
                    # Read file content
                    with z.open(name) as f:
                        # Attempt to decode as utf-8
                        text_content = f.read().decode('utf-8')
                        all_text.append(text_content)
                except (UnicodeDecodeError, zipfile.BadZipFile):
                    # Skip files that aren't valid text/utf-8
                    continue
            
            # Join all extracted text with newlines
            result = "\n".join(all_text)
            return web.Response(text=result, content_type='text/plain')

    except Exception as e:
        return web.response.text(f"Invalid input: {str(e)}", status=400)

async def init_app():
    app = web.Application()
    app.router.add_post('/convert', convert_zip_to_txt)
    return app

if __name__ == '__main__':
    app = web.Application()
    app.router.add_post('/convert', convert_zip_to_txt)
    web.run_app(app, host='0.0.0.0', port=5000)