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

        frame_number = int(frame_number)
        
        # Use temporary directory to handle files
        with tempfile.TemporaryDirectory() as tmpdir:
            video_path = os.path.join(tmpdir, 'input_video')
            output_path = os.path.join(tmpdir, 'frame.png')
            
            # Save uploaded file to disk
            with open(video_path, 'wb+') as destination:
                for chunk in video_file.chunks():
                    destination.write(chunk)
            
            # FFmpeg command to extract a specific frame
            # -vframes 1: extract one frame
            # -vf "select=eq(n\,X)": select frame index X
            # Note: frame numbers in ffmpeg are 0-indexed
            cmd = [
                'ffmpeg',
                '-vframes', '1',
                '-vf', f'select=eq(n\\,{frame_number})',
                '-i', video_path,
                '-f', 'image2',
                output_path
            ]
            
            process = subprocess.run(cmd, capture_output=True, text=True)
            
            if process.returncode != 0 or not os.path.exists(output_path):
                return JsonResponse({'error': f'Frame at index {frame_number} could not be found.'}, status=404)
            
            with open(output_path, 'rb') as f:
                img_data = f.read()
                
            return HttpResponse(img_data, content_type='image/png')

    except ValueError:
        return JsonResponse({'error': 'frameNumber must be an integer'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)