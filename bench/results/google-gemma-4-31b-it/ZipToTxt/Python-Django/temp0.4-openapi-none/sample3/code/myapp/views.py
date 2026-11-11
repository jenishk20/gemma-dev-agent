import zipfile
import io
from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def convert_zip_to_txt(request):
    if request.method != 'POST':
        return HttpResponseBadRequest("Only POST requests are allowed")

    if 'file' not in request.FILES:
        return HttpResponseBadRequest("No file uploaded")

    zip_file = request.FILES['file']
    
    try:
        # Use BytesIO to read the uploaded file as a zip archive
        with zipfile.ZipFile(zip_file) as z:
            output_text = []
            # Get list of files in zip and sort them to ensure consistent order
            for filename in sorted(z.namelist()):
                # Only process files (not directories)
                if not z.getinfo(filename).is_dir():
                    try:
                        # Read content and decode as utf-8
                        with z.open(filename) as f:
                            content = f.read().decode('utf-8')
                            output_text.append(content)
                    except (UnicodeDecodeError, Exception):
                        # Skip files that are not valid text files
                        continue
            
            # Join all contents with a newline
            final_text = "\n".join(output_text)
            return HttpResponse(final_text, content_type="text/plain")
            
    except zipfile.BadZipFile:
        return HttpResponseBadRequest("Invalid zip file")
    except Exception as e:
        return HttpResponseBadRequest(f"An error occurred: {str(e)}")