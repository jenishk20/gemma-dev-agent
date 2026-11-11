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
        # Use io.BytesIO to handle the uploaded file in memory
        with zipfile.ZipFile(zip_file) as z:
            combined_text = []
            # Iterate through all files in the zip
            for filename in z.namelist():
                # Only process files that are not directories
                if not filename.endswith('/'):
                    with z.open(filename) as f:
                        try:
                            # Decode as utf-8, ignore errors for binary files
                            content = f.read().decode('utf-8', errors='ignore')
                            combined_text.append(content)
                        except Exception:
                            continue
            
            # Join all contents with a newline
            result = "\n".join(combined_text)
            return HttpResponse(result, content_type="text/plain")
            
    except zipfile.BadZipFile:
        return HttpResponseBadRequest("Invalid zip file")
    except Exception as e:
        return HttpResponseBadRequest(f"An error occurred: {str(e)}")