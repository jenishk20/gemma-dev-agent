import zipfile
import io
from django.http import HttpResponse, HttpResponseBadRequest

def convert_zip_to_txt(request):
    if request.method != 'POST':
        return HttpResponseBadRequest("Only POST requests are allowed")

    try:
        uploaded_file = request.FILES.get('file')
        if not uploaded_file:
            return HttpResponseBadRequest("No file uploaded")

        # Use io.BytesIO to handle the uploaded file in memory
        zip_data = io.BytesIO(uploaded_file.read())
        
        with zipfile.ZipFile(zip_data) as z:
            # Filter for files that look like text files (ending in .txt)
            # or attempt to read all files if the requirement is "all text files"
            # Standard approach: read files that end with .txt or are identified as text
            text_contents = []
            
            # Sort files by name to ensure consistent concatenation order
            for filename in sorted(z.namelist()):
                # We only process files, not directories
                if not z.getinfo(filename).is_dir():
                    try:
                        with z.open(filename) as f:
                            # Attempt to decode as utf-8
                            content = f.read().decode('utf-8')
                            text_contents.append(content)
                    except (UnicodeDecodeError, zipfile.BadZipFile):
                        # Skip binary files or corrupted entries
                        continue
            
            # Join all contents with a newline
            final_text = "\n".join(text_contents)
            return HttpResponse(final_text, content_type="text/plain")

    except zipfile.BadZipFile:
        return HttpResponseBadRequest("Invalid zip file")
    except Exception as e:
        return HttpResponseBadRequest(f"An error occurred: {str(e)}")