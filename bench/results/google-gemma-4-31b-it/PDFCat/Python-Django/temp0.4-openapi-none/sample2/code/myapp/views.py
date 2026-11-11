import os
import subprocess
import tempfile
import shutil
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

        # Create a temporary directory to store uploaded files and the result
        with tempfile.TemporaryDirectory() as tmpdir:
            input_paths = []
            
            # Save uploaded files to the temp directory
            for i, f in enumerate(files):
                # Ensure we only process PDF files
                if not f.name.lower().endswith('.pdf'):
                    return JsonResponse({'error': 'Only PDF files are allowed.'}, status=400)
                
                file_path = os.path.join(tmpdir, f"input_{i}.pdf")
                with open(file_path, 'wb+') as destination:
                    for chunk in f.chunks():
                        destination.write(chunk)
                input_paths.append(file_path)

            output_path = os.path.join(tmpdir, "concatenated.pdf")
            
            # Construct the pdfunite command
            # pdfunite input1.pdf input2.pdf ... output.pdf
            command = ['pdfunite'] + input_paths + [output_path]
            
            try:
                subprocess.run(command, check=True, capture_output=True)
            except subprocess.CalledProcessError as e:
                return JsonResponse({'error': f"pdfunite failed: {e.stderr.decode()}"}, status=500)

            # Read the resulting PDF and return it
            with open(output_path, 'rb') as f:
                pdf_content = f.read()
            
            return HttpResponse(pdf_content, content_type='application/pdf')

    except Exception as e:
        return JsonResponse({'error': f"An error occurred while processing the files: {str(e)}"}, status=500)