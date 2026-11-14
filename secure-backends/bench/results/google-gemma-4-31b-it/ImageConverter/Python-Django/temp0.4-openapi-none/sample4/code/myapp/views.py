import os
import subprocess
import tempfile
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def create_gif(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        # Extract parameters
        images = request.FILES.getlist('images')
        target_size = request.POST.get('targetSize')
        delay = request.POST.get('delay', '10')
        append_reverted = request.POST.get('appendReverted', 'false').lower() == 'true'

        if not images or not target_size:
            return JsonResponse({'error': 'Missing required fields: images and targetSize'}, status=400)

        # Validate targetSize format (e.g., 500x500)
        if 'x' not in target_size:
            return JsonResponse({'error': 'targetSize must be in format WxH (e.g. 500x500)'}, status=400)

        # Create a temporary directory to store image frames
        with tempfile.TemporaryDirectory() as tmpdir:
            input_files = []
            for i, img_file in enumerate(images):
                path = os.path.join(tmpdir, f"frame_{i}.tmp")
                with open(path, 'wb') as f:
                    for chunk in img_file.chunks():
                        f.write(chunk)
                input_files.append(path)

            # Handle appendReverted: duplicate images in reverse order
            if append_reverted:
                reverted_files = input_files[::-1]
                # We need to save them as separate files to avoid ImageMagick confusion
                reverted_paths = []
                for i, path in enumerate(reverted_files):
                    new_path = os.path.join(tmpdir, f"rev_{i}.tmp")
                    with open(new_path, 'wb') as f_out:
                        with open(path, 'rb') as f_in:
                            f_out.write(f_in.read())
                    reverted_paths.append(new_path)
                input_files.extend(reverted_paths)

            output_gif = os.path.join(tmpdir, "result.gif")
            
            # Build ImageMagick command
            # -delay is in ticks (1/100th of a second). 
            # The API says delay is in milliseconds. 100ms = 10 ticks.
            try:
                delay_ticks = int(delay) // 10
            except ValueError:
                delay_ticks = 1

            cmd = [
                'convert',
                '-delay', str(delay_ticks),
                '-resize', target_size,
                *input_files,
                output_gif
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                return JsonResponse({'error': f"ImageMagick error: {result.stderr}"}, status=500)

            with open(output_gif, 'rb') as f:
                gif_data = f.read()

            return HttpResponse(gif_data, content_type='image/gif')

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)