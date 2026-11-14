import subprocess
import tempfile
import os
from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def convert_pdf_to_text(request):
    if request.method != 'POST':
        return HttpResponseBadRequest("Only POST requests are allowed")

    if 'file' not in request.FILES:
        return HttpResponseBadRequest("Missing file in request")

    pdf_file = request.FILES['file']
    
    # Basic validation for PDF extension
    if not pdf_file.name.lower().endswith('.pdf'):
        return HttpResponseBadRequest("Uploaded file must be a PDF")

    # Create temporary files for input and output
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_pdf:
        for chunk in pdf_file.chunks():
            temp_pdf.write(chunk)
        temp_pdf_path = temp_pdf.name

    temp_txt_path = temp_pdf_path + ".txt"

    try:
        # Use pdftotext utility from poppler-utils
        # Command: pdftotext <input_pdf> <output_txt>
        result = subprocess.run(
            ['pdftotext', temp_pdf_path, temp_txt_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        if result.returncode != 0:
            return HttpResponse("Internal Server Error - Conversion failed", status=500)

        # Read the generated text file
        if os.path.exists(temp_txt_path):
            with open(temp_txt_path, 'r', encoding='utf-8') as f:
                text_content = f.read()
            return HttpResponse(text_content, content_type='text/plain')
        else:
            return HttpResponse("Internal Server Error - Text file not generated", status=500)

    except Exception as e:
        return HttpResponse(f"Internal Server Error: {str(e)}", status=500)
    finally:
        # Cleanup temporary files
        if os.path.exists(temp_pdf_path):
            os.remove(temp_pdf_path)
        if os.path.exists(temp_txt_path):
            os.remove(temp_txt_path)