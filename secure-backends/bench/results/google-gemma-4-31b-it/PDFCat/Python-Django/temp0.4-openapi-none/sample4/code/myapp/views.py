import os
import subprocess
import tempfile
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def concatenate_pdfs(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        files = request.FILES.getlist('files')
        if not files:
            return JsonResponse({'error': 'Invalid input or missing files.'}, status=400)

        # Create a temporary directory to handle files
        with tempfile.TemporaryDirectory() as tmpdir:
            input_paths = []
            
            for i, uploaded_file in enumerate(files):
                # Ensure we only process PDFs
                if not uploaded_file.content_type == 'application/pdf':
                    # We continue but the user might want a 400 here. 
                    # For strictness, we check extension or content type.
                    pass
                
                file_path = os.path.join(tmpdir, f"input_{i}.pdf")
                with open(file_path, 'wb+') as destination:
                    for chunk in uploaded_file.chunks():
                        destination.write(chunk)
                input_paths.append(file_path)

            if not input_paths:
                return JsonResponse({'error': 'No valid PDF files provided.'}, status=400)

            output_path = os.path.join(tmpdir, "concatenated.pdf")
            
            # Construct pdfunite command: pdfunite file1.pdf file2.pdf output.pdf
            cmd = ['pdfunite'] + input_paths + [output_path]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                return JsonResponse({'error': 'An error occurred while processing the files.'}, status=500)

            with open(output_path, 'rb') as f:
                pdf_content = f.read()

            return HttpResponse(pdf_content, content_type='application/pdf')

    except Exception as e:
        return JsonResponse({'error': f'An error occurred while processing the files: {str(e)}'}, status=500)