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

        # Create a temporary directory to hold the files
        with tempfile.TemporaryDirectory() as tmpdir:
            input_paths = []
            for i, f in enumerate(files):
                # Ensure we only process PDFs
                if not f.content_type == 'application/pdf' and not f.name.lower().endswith('.pdf'):
                    return JsonResponse({'error': 'All files must be PDFs.'}, status=400)
                
                file_path = os.path.join(tmpdir, f'input_{i}.pdf')
                with open(file_path, 'wb') as destination:
                    for chunk in f.chunks():
                        destination.write(chunk)
                input_paths.append(file_path)

            output_path = os.path.join(tmpdir, 'concatenated.pdf')
            
            # pdfunite takes: pdfunite input1.pdf input2.pdf ... output.pdf
            cmd = ['pdfunite'] + input_paths + [output_path]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                return JsonResponse({'error': 'An error occurred while processing the files.'}, status=500)

            with open(output_path, 'rb') as f:
                content = f.read()
                return HttpResponse(content, content_type='application/pdf')

    except Exception as e:
        return JsonResponse({'error': str(e) if not DEBUG else 'Internal Server Error'}, status=500)

# Note: DEBUG is not defined here, using a safe fallback
DEBUG = False