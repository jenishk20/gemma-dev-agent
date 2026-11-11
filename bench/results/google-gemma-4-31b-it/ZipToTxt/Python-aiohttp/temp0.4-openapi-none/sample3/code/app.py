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
        reader = await request.multipart()
        file_data = None

        while True:
            part = await reader.next()
            if part is None:
                break
            if part.name == 'file':
                # Read the binary content of the uploaded file
                file_data = await part.read()
                break

        if file_data is None:
            return web.Response(text="No file uploaded", status=400)

        # Use BytesIO to treat the binary data as a file-like object for zipfile
        with zipfile.ZipFile(io.BytesIO(file_data)) as z:
            # Get list of all files in the zip
            file_list = z.namelist()
            combined_text = []

            for file_name in file_list:
                # We only process files (ignore directories)
                # In a real scenario, we might check extensions, but here we attempt to read all
                try:
                    with z.open(file_name) as f:
                        # Read bytes and decode to utf-8, ignoring errors for non-text files
                        content = f.read().decode('utf-8', errors='ignore')
                        if content:
                            combined_text.append(content)
                except Exception:
                    # Skip files that cannot be read
                    continue

            # Join all contents with a newline
            final_output = "\n".join(combined_text)
            return web.Response(text=final_output, content_type='text/plain')

    except zipfile.BadZipFile:
        return web.Response(text="Invalid zip file", status=400)
    except Exception as e:
        return web.Response(text=f"An error occurred: {str(e)}", status=400)

async def init_app():
    app = web.Application()
    app.router.add_post('/convert', convert_zip_to_txt)
    return app

if __name__ == '__main__':
    app = None
    # We use a helper to run the app since init_app is async
    import asyncio
    
    async def main():
        global app
        app = await init_app()
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', 5000)
        await site.start()
        print("Server started at http://0.0.0.0:5000")
        # Keep the server running forever
        await asyncio.Event().wait()

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass