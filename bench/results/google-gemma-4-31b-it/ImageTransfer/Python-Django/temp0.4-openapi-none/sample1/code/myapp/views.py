from django.http import JsonResponse, FileResponse
from django.views.decorators.csrf import csrf_exempt
from .models import ImageUpload
import mimetypes

@csrf_exempt
def upload_image(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        uploaded_file = request.FILES.get('file')
        if not uploaded_file:
            return JsonResponse({'error': 'No file provided'}, status=400)
        
        img_obj = ImageUpload.objects.create(file=uploaded_file)
        return JsonResponse({'id': str(img_obj.id)}, status=200)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def serve_image(request, imageId):
    try:
        img_obj = ImageUpload.objects.get(id=imageId)
        file_handle = img_obj.file.open()
        
        # Determine content type based on the file extension
        content_type, _ = mimetypes.guess_type(img_obj.file.name)
        if not content_type:
            content_type = 'application/octet-stream'
            
        response = FileResponse(file_handle, content_type=content_type)
        # 'inline' ensures the browser tries to render it rather than download it
        response['Content-Disposition'] = f'inline; filename="{img_obj.file.name}"'
        return response
    except ImageUpload.DoesNotExist:
        return JsonResponse({'error': 'Image not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)