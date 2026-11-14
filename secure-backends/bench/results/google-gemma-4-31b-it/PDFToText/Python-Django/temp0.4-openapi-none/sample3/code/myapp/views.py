import os
import subprocess
import tempfile
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def convert_pdf_to_text(request):
    if request.method != 'POST':
        return HttpResponse("Method Not Allowed", status=405)

    try:
        # Retrieve the file from the request
        uploaded_file = request.FILES.get('file')
        if not uploaded_file:
            return HttpResponse("Bad Request - Missing file", status=400)

        if not uploaded_file.content_type == 'application/pdf':
            # We check content type, but also check extension if needed
            if not uploaded_file.name.lower().endswith('.pdf'):
                return HttpResponse("Bad Request - Invalid file type", status=400)

        # Create temporary files for input and output
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_pdf:
            for chunk in uploaded_file.chunks():
                temp_pdf.write(chunk)
            temp_pdf_path = temp_pdf.name

        try:
            # Use pdftotext utility
            # -layout maintains the layout of the text
            # We output to stdout by not providing an output filename
            result = subprocess.run(
                ['pdftotext', temp_pdf_path, '-'],
                capture_output=True,
                text=True,
                check=True
            )
            
            return HttpResponse(result.stdout, content_type='text/plain')

        except subprocess.CalledProcessError as e:
            return HttpResponse(f"Internal Server Error - Conversion failed: {str(e)}", status=500)
        finally:
            # Cleanup temporary PDF file
            if os.path.exists(temp_pdf_path):
                os.remove(temp_pdf_path)

    except Exception as e:
        return HttpResponse(f"Internal Server Error - {str(e)}", status=500)