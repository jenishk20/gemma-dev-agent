import os
import subprocess
import tempfile
import shutil
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def create_gif(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        # Extract parameters from request
        images = request.FILES.getlist('images')
        target_size = request.POST.get('targetSize')
        delay = request.POST.get('delay', '10')
        append_reverted = request.POST.get('appendReverted', 'false').lower() == 'true'

        if not images or not target_size:
            return JsonResponse({'error': 'Missing required fields: images and targetSize'}, status=400)

        # Create a temporary directory to store images
        with tempfile.TemporaryDirectory() as tmpdir:
            input_files = []
            for i, img_file in enumerate(images):
                path = os.path.join(tmpdir, f"frame_{i}.tmp")
                with open(path, 'wb') as f:
                    for chunk in img_file.chunks():
                        f.write(chunk)
                input_files.append(path)

            # Handle appendReverted: duplicate the list in reverse order
            if append_reverted:
                # We need to copy files to avoid ImageMagick reading the same file twice if it's a stream
                # but since they are on disk, we just add the paths in reverse
                frames = input_files + input_files[::-1]
            else:
                frames = input_files

            output_gif = os.path.join(tmpdir, "result.gif")
            
            # ImageMagick 'convert' command construction
            # -delay: time between frames in ticks (usually 1/100th of a second)
            # The API specifies delay in milliseconds. ImageMagick -delay is in 1/100s.
            # So 100ms = 10 ticks.
            try:
                delay_ticks = int(delay) // 10
            except ValueError:
                delay_ticks = 1

            cmd = [
                'convert',
                '-delay', str(delay_ticks),
                '-resize', target_size,
                *frames,
                output_gif
            ]

            process = subprocess.run(cmd, capture_output=True, text=True)

            if process.returncode != 0:
                return JsonResponse({'error': f"ImageMagick error: {process.stderr}"}, status=500)

            with open(output_gif, 'rb') as f:
                return HttpResponse(f.read(), content_type='image/gif')

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)