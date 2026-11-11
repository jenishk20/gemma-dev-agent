import os
import subprocess
import tempfile
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def create_gif_view(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method is allowed'}, status=405)

    try:
        # Get parameters from request
        images = request.FILES.getlist('images')
        target_size = request.POST.get('targetSize')
        delay = request.POST.get('delay', '10')
        append_reverted = request.POST.get('appendReverted', 'false').lower() == 'true'

        if not images or not target_size:
            return JsonResponse({'error': 'Missing required parameters: images and targetSize'}, status=400)

        # Create a temporary directory to store frames
        with tempfile.TemporaryDirectory() as tmpdir:
            input_files = []
            for i, img_file in enumerate(images):
                path = os.path.join(tmpdir, f"frame_{i}.png")
                with open(path, 'wb') as f:
                    for chunk in img_file.chunks():
                        f.write(chunk)
                input_files.append(path)

            # If appendReverted is true, add images in reverse order
            if append_reverted:
                # We skip the very last image to avoid a double frame at the peak of the animation
                # but the prompt says "append a reverted version", usually meaning the sequence back
                reverted_files = input_files[::-1]
                # To avoid duplication of the last frame, we can slice it, 
                # but standard "ping-pong" usually keeps the sequence.
                # Let's follow the literal "append a reverted version".
                input_files.extend(reverted_files)

            output_gif = os.path.join(tmpdir, "result.gif")
            
            # ImageMagick convert command
            # -delay is in ticks (1/100th of a second). 
            # The API specifies delay in milliseconds. 
            # 100ms = 10 ticks.
            try:
                delay_ticks = int(delay) // 10
            except ValueError:
                delay_ticks = 1

            # Construct the command
            # convert -delay <ticks> -loop 0 <files> -resize <size> <output>
            cmd = [
                'convert',
                '-delay', str(delay_ticks),
                '-loop', '0'
            ]
            cmd.extend(input_files)
            cmd.extend(['-resize', target_size, output_gif])

            process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            if process.returncode != 0:
                return JsonResponse({'error': f'ImageMagick error: {process.stderr.decode()}'}, status=500)

            with open(output_gif, 'rb') as f:
                gif_data = f.read()

            return HttpResponse(gif_data, content_type='image/gif')

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)