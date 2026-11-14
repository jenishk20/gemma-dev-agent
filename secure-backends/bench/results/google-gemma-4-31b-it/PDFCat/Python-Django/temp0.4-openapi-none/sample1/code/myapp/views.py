import os
import subprocess
import tempfile
from django.http import HttpResponse, JsonResponse

def concatenate_pdfs(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    files = request.FILES.getlist('files')
    
    if not files:
        return JsonResponse({'error': 'Invalid input or missing files.'}, status=400)

    # Create a temporary directory to store the input and output PDFs
    with tempfile.TemporaryDirectory() as tmpdir:
        input_paths = []
        try:
            # Save uploaded files to the temp directory
            for i, f in enumerate(files):
                # Basic validation: check if it's a PDF (by extension or content type)
                if not f.name.lower().endswith('.pdf'):
                    return JsonResponse({'error': 'One or more uploaded files are not PDFs.'}, status=400)
                
                path = os.path.join(tmpdir, f'input_{i}.pdf')
                with open(path, 'wb') as destination:
                    for chunk in f.chunks():
                        destination.write(chunk)
                input_paths.append(path)

            output_path = os.path.join(tmpdir, 'concatenated.pdf')
            
            # Construct the pdfunite command
            # pdfunite input1.pdf input2.pdf ... output.pdf
            command = ['pdfunite'] + input_paths + [output_path]
            
            result = subprocess.run(command, capture_output=True, text=True)
            
            if result.returncode != 0:
                return JsonResponse({'error': 'An error occurred while processing the files.'}, status=500)

            # Read the resulting PDF and return it
            with open(output_path, 'rb') as f:
                pdf_content = f.read()
            
            return HttpResponse(pdf_content, content_type='application/pdf')

        except Exception as e:
            return JsonResponse({'error': f'An error occurred while processing the files: {str(e)}'}, status=500)