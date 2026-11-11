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
        frame_number_str = request.POST.get('frameNumber')
        
        if not video_file or not frame_number_str:
            return JsonResponse({'error': 'Missing video or frameNumber'}, status=400)
        
        frame_number = int(frame_number_str)
        
        # Create temporary directory for processing
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = os.path.join(tmpdir, 'input_video')
            output_path = os.path.join(tmpdir, 'output_frame.png')
            
            # Save uploaded file to disk
            with open(input_path, 'wb+') as destination:
                for chunk in video_file.chunks():
                    destination.write(chunk)
            
            # ffmpeg command: extract a single frame at the given index
            # -i: input file
            # -vf "select=eq(n\,X)": select frame X
            # -vframes 1: output only one frame
            cmd = [
                'ffmpeg',
                '-i', input_path,
                '-vf', f'select=eq(n\,{frame_number})',
                '-vframes', '1',
                '-f', 'image2',
                '-vcodec', 'png',
                output_path
            ]
            
            process = subprocess.run(cmd, capture_output=True, text=True)
            
            if process.returncode != 0 or not os.path.exists(output_path):
                return JsonResponse({'error': f'Frame at index {frame_number} could not be found.'}, status=404)
            
            with open(output_path, 'rb') as f:
                image_bytes = f.read()
                
            return HttpResponse(image_bytes, content_type='image/png')
            
    except ValueError:
        return JsonResponse({'error': 'frameNumber must be an integer'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)