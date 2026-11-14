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
            return JsonResponse({'error': 'Missing required fields'}, status=400)

        frame_number = int(frame_number)
        
        # Create temporary files for input and output
        with tempfile.NamedTemporaryFile(suffix='.tmp', delete=False) as input_tmp:
            for chunk in video_file.chunks():
                input_tmp.write(chunk)
            input_path = input_tmp.name

        output_path = input_path + '.png'
        
        try:
            # ffmpeg command to extract a specific frame
            # -i: input file
            # -vf "select=not(mod(n,1))": select frame (n is frame index)
            # -vframes 1: output exactly one frame
            # We use the 'select' filter to pick the specific frame index
            cmd = [
                'ffmpeg', 
                '-i', input_path, 
                '-vf', f'select=eq(n,{frame_number})', 
                '-vframes', '1', 
                '-f', 'image2', 
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0 or not os.path.exists(output_path):
                # If ffmpeg failed or file wasn't created, frame might be out of range
                return JsonResponse({'error': f'Frame at index {frame_number} could not be found.'}, status=404)

            with open(output_path, 'rb') as f:
                image_data = f.read()
            
            return HttpResponse(image_data, content_type='image/png')

        finally:
            # Cleanup temporary files
            if os.path.exists(input_path):
                os.remove(input_path)
            if os.path.exists(output_path):
                os.remove(output_path)

    except ValueError:
        return JsonResponse({'error': 'frameNumber must be an integer'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)