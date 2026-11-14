import os
import subprocess
import tempfile
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def create_gif_view(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        # Extract parameters from request.POST
        target_size = request.POST.get('targetSize')
        delay = request.POST.get('delay', '10')
        append_reverted = request.POST.get('appendReverted', 'false').lower() == 'true'
        
        # Extract images from request.FILES
        images = request.FILES.getlist('images')

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

            # Handle appendReverted: Duplicate the list in reverse order
            if append_reverted:
                # We need to copy the files to new paths so ImageMagick treats them as separate frames
                reverted_files = []
                for i, path in enumerate(reversed(input_files)):
                    rev_path = os.path.join(tmpdir, f"rev_{i}.tmp")
                    with open(rev_path, 'wb') as f_out:
                        with open(path, 'rb') as f_in:
                            f_out.write(f_in.read())
                    reverted_files.append(rev_path)
                input_files.extend(reverted_files)

            output_gif = os.path.join(tmpdir, "result.gif")
            
            # ImageMagick 'convert' command
            # -delay: delay between frames (in 1/100ths of a second, so multiply ms by 0.01)
            # -resize: target size (e.g., 500x500)
            # -loop 0: infinite loop
            
            # Convert ms to ImageMagick ticks (1 tick = 10ms)
            try:
                im_delay = int(delay) // 10
            except ValueError:
                im_delay = 1

            cmd = [
                'convert',
                '-delay', str(im_delay),
                '-loop', '0',
                '-resize', target_size,
            ]
            cmd.extend(input_files)
            cmd.append(output_gif)

            # Execute the command
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                return JsonResponse({'error': f"ImageMagick error: {result.stderr}"}, status=500)

            with open(output_gif, 'rb') as f:
                gif_data = f.read()

            return HttpResponse(gif_data, content_type='image/gif')

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)