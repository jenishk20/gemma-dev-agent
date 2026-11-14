import os
import subprocess
import tempfile
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def concatenate_pdfs(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method is allowed'}, status=405)

    # The OpenAPI schema specifies a field named 'files' as an array
    files = request.FILES.getlist('files')

    if not files:
        return JsonResponse({'error': 'Invalid input or missing files.'}, status=400)

    # Create a temporary directory to store the PDF fragments and the result
    with tempfile.TemporaryDirectory() as tmpdir:
        input_paths = []
        try:
            # Save uploaded files to the temp directory
            for i, f in enumerate(files):
                # Ensure we only process PDFs
                if not f.name.lower().endswith('.pdf'):
                    return JsonResponse({'error': f'File {f.name} is not a PDF.'}, status=400)
                
                file_path = os.path.join(tmpdir, f'input_{i}.pdf')
                with open(file_path, 'wb+') as destination:
                    for chunk in f.chunks():
                        destination.write(chunk)
                input_paths.append(file_path)

            output_path = os.path.join(tmpdir, 'concatenated.pdf')
            
            # Construct the pdfunite command: pdfunite file1.pdf file2.pdf ... output.pdf
            command = ['pdfunite'] + input_paths + [output_path]
            
            # Execute the CLI tool
            result = subprocess.run(command, capture_output=True, text=True)
            
            if result.returncode != 0:
                return JsonResponse({'error': f'pdfunite error: {result.stderr}'}, status=500)

            # Read the resulting file and return it as a PDF response
            with open(output_path, 'rb') as f:
                pdf_content = f.read()
            
            return HttpResponse(pdf_content, content_type='application/pdf')

        except Exception as e:
            return JsonResponse({'error': f'An error occurred while processing the files: {str(e)}'}, status=500)