import zipfile
import io
from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def convert_zip_to_txt(request):
    if request.method != 'POST':
        return HttpResponseBadRequest("Only POST requests are allowed")

    if 'file' not in request.FILES:
        return HttpResponseBadRequest("Missing 'file' in request body")

    zip_file = request.FILES['file']
    
    try:
        # Use io.BytesIO to read the uploaded file as a binary stream
        with zipfile.ZipFile(zip_file) as z:
            combined_text = []
            # Get list of files in the zip
            for filename in z.namelist():
                # We only process files that look like text files or are not directories
                # In a real scenario, we might check extensions, but here we attempt to read
                # and concatenate contents of all files that aren't directories.
                if not z.getinfo(filename).is_dir():
                    with z.open(filename) as f:
                        try:
                            content = f.read().decode('utf-8')
                            combined_text.append(content)
                        except UnicodeDecodeError:
                            # Skip binary files that cannot be decoded as utf-8
                            continue
            
            result = "\n".join(combined_text)
            return HttpResponse(result, content_type="text/plain")
            
    except zipfile.BadZipFile:
        return HttpResponseBadRequest("Invalid zip file")
    except Exception as e:
        return HttpResponseBadRequest(f"An error occurred: {str(e)}")