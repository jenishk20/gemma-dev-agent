import os
import subprocess
import tempfile
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def extract_frame(request):
    if request.method != 'POST':
        return HttpResponse(status=405)

    try:
        video_file = request.FILES.get('video')
        frame_number = request.POST.get('frameNumber')
        
        if not video_file or frame_number is None:
            return JsonResponse({'error': 'Missing video or frameNumber'}, status=400)

        # Create temporary directory for processing
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = os.path.join(tmpdir, 'input_video')
            output_path = os.path.join(tmpdir, 'output_frame.png')

            # Save uploaded video to disk
            with open(input_path, 'wb+') as destination:
                for chunk in video_file.chunks():
                    destination.write(chunk)

            # Use ffmpeg to extract the specific frame
            # -i: input file
            # -vf: video filter (select frame by index)
            # -vframes 1: output exactly one frame
            cmd = [
                'ffmpeg',
                '-i', input_path,
                '-vf', f'select=eq(n,{frame_number})',
                '-vframes', '1',
                output_path,
                '-y' # overwrite output
            ]
            
            process = subprocess.run(cmd, capture_output=True, text=True)
            
            if process.returncode != 0 or not os.path.exists(output_path):
                return JsonResponse({'error': f'Frame at index {frame_number} could not be found.'}, status=404)

            with open(output_path, 'rb') as f:
                return HttpResponse(f.read(), content_type='image/png')

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)