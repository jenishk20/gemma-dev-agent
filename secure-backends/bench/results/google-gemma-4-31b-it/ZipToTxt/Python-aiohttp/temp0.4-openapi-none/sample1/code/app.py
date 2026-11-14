import io
import zipfile
from aiohttp import web

async def convert_zip_to_txt(request):
    """
    Handles the POST /convert endpoint.
    Expects a multipart/form-data request with a 'file' field containing a zip archive.
    """
    try:
        # Read the multipart form data
        data = await request.post()
        
        if 'file' not in data:
            return web.response.text("Missing 'file' field in request", status=400)
        
        file_field = data['file']
        filename = file_field.filename
        content = file_field.file.read()

        # Use io.BytesIO to treat the bytes as a file-like object for zipfile
        with zipfile.ZipFile(io.BytesIO(content)) as z:
            # Get a list of all files in the zip
            namelist = z.namelist()
            
            output_texts = []
            for name in namelist:
                # We only want to process files, not directories
                # ZipFile.getinfo helps check if it's a directory
                info = z.getinfo(name)
                if info.is_dir():
                    continue
                
                try:
                    # Read the content of the file
                    with z.open(name) as f:
                        # Attempt to decode as utf-8, ignore errors for non-text files
                        text_content = f.read().decode('utf-8', errors='ignore')
                        output_texts.append(text_content)
                except Exception:
                    # If a file cannot be read, we skip it
                    continue

            # Join all extracted text contents with newlines
            final_text = "\n".join(output_texts)
            
            return web.Response(text=final_text, content_type='text/plain')

    except zipfile.BadZipFile:
        return web.response.text("Invalid zip file provided", status=400)
    except Exception as e:
        return web.response.text(f"An error occurred: {str(e)}", status=400)

async def init_app():
    app = web.Application()
    app.router.add_post('/convert', convert_zip_to_txt)
    return app

if __name__ == '__main__':
    app = web.Application()
    app.router.add_post('/convert', convert_zip_to_txt)
    web.run_app(app, host='0.0.0.0', port=5000)