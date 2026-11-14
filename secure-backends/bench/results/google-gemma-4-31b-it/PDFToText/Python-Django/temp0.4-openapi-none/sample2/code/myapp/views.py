import subprocess
import tempfile
import os
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

@csrf_exempt
@require_http_methods(["POST"])
def convert_pdf_to_text(request):
    try:
        if 'file' not in request.FILES:
            return HttpResponse("Bad Request - Missing file", content_type="text/plain", status=400)
        
        pdf_file = request.FILES['file']
        
        if not pdf_file.content_type == 'application/pdf':
            # We check extension as well since content_type can be unreliable
            if not pdf_file.name.lower().endswith('.pdf'):
                return HttpResponse("Bad Request - Invalid file type", content_type="text/plain", status=400)

        # Create temporary files for input and output
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
            for chunk in pdf_file.chunks():
                temp_pdf.write(chunk)
            temp_pdf_path = temp_pdf.name

        try:
            # Use pdftotext utility from poppler-utils
            # -q suppresses warnings, -layout attempts to preserve layout
            result = subprocess.run(
                ['pdftotext', temp_pdf_path, '-'], 
                capture_output=True, 
                text=True, 
                check=True
            )
            text_content = result.stdout
            return HttpResponse(text_content, content_type="text/plain")
        
        except subprocess.CalledProcessError as e:
            return HttpResponse(f"Internal Server Error - Conversion failed: {str(e)}", content_type="text/plain", status=500)
        finally:
            if os.path.exists(temp_pdf_path):
                os.remove(temp_pdf_path)

    except Exception as e:
        return HttpResponse(f"Internal Server Error - {str(e)}", content_type="text/plain", status=500)