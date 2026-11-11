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
        # Use io.BytesIO to read the uploaded file as a binary stream
        with zipfile.ZipFile(io.BytesIO(zip_file.read())) as z:
            output_text = []
            # Get list of all files in the zip
            for name in z.namelist():
                # Only process files (not directories)
                if not name.endswith('/'):
                    try:
                        # Read the content of the file
                        with z.open(name) as f:
                            content = f.read().decode('utf-8')
                            output_text.append(content)
                    except (UnicodeDecodeError, zipfile.BadZipFile):
                        # Skip files that aren't valid text files
                        continue
            
            # Join all contents with a newline
            final_text = "\n".join(output_text)
            return HttpResponse(final_text, content_type='text/plain')
            
    except zipfile.BadZipFile:
        return HttpResponseBadRequest("Invalid zip file")
    except Exception as e:
        return HttpResponseBadRequest(f"An error occurred: {str(e)}")