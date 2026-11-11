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
        uploaded_file = request.FILES.get('file')
        if not uploaded_file:
            return HttpResponse("Bad Request - Missing file", status=400)
        
        if not uploaded_file.content_type == 'application/pdf':
            # We check extension as well just in case
            if not uploaded_file.name.lower().endswith('.pdf'):
                return HttpResponse("Bad Request - File is not a PDF", status=400)

        # Create temporary files for input and output
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_pdf:
            for chunk in uploaded_file.chunks():
                temp_pdf.write(chunk)
            temp_pdf_path = temp_pdf.name

        try:
            # pdftotext <input.pdf> - outputs to stdout if no output file is specified
            # We use subprocess to call the poppler-utils tool
            result = subprocess.run(
                ['pdftotext', temp_pdf_path, '-'],
                capture_output=True,
                text=True,
                check=True
            )
            
            return HttpResponse(result.stdout, content_type='text/plain')
        
        except subprocess.CalledProcessError:
            return HttpResponse("Internal Server Error - Conversion failed", status=500)
        finally:
            if os.path.exists(temp_pdf_path):
                os.remove(temp_pdf_path)

    except Exception as e:
        return HttpResponse(f"Internal Server Error - {str(e)}", status=500)