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

        # Create a temporary directory to store frames
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
                # We skip the last image to avoid a double frame at the peak of the loop
                # but the schema implies "append a reverted version", so we'll just reverse the whole list.
                reverted_files = input_files[::-1]
                # To avoid duplicating the very last frame of the forward sequence as the first of the reverse:
                # we usually slice it, but for simplicity and strict adherence to "append reverted version", 
                # we just add them.
                all_frames = input_files + reverted_files
            else:
                all_frames = input_files

            output_gif = os.path.join(tmpdir, "result.gif")
            
            # ImageMagick 'convert' command
            # -delay: time between frames (1/100th of a second in IM, but schema says ms)
            # IM delay is in ticks. Usually 1 tick = 10ms. So delay/10.
            try:
                delay_ticks = int(delay) // 10
            except ValueError:
                delay_ticks = 1

            # Command: convert -delay <d> -resize <size> <files> <output>
            cmd = [
                'convert',
                '-delay', str(delay_ticks),
                '-resize', target_size,
                *all_frames,
                output_gif
            ]

            process = subprocess.run(cmd, capture_output=True, text=True)
            
            if process.returncode != 0:
                return JsonResponse({'error': f'ImageMagick error: {process.stderr}'}, status=500)

            with open(output_gif, 'rb') as f:
                return HttpResponse(f.read(), content_type='image/gif')

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)