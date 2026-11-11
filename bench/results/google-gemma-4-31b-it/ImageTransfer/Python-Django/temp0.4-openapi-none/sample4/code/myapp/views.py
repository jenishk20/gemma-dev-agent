from django.http import JsonResponse, FileResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from .models import ImageFile
import os

@csrf_exempt
def upload_image(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        if 'file' not in request.FILES:
            return JsonResponse({'error': 'No file provided'}, status=400)
        
        uploaded_file = request.FILES['file']
        image_obj = ImageFile.objects.create(file=uploaded_file)
        
        return JsonResponse({'id': str(image_obj.id)}, status=200)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def serve_image(request, imageId):
    try:
        image_obj = ImageFile.objects.get(id=imageId)
        # FileResponse automatically handles content-type based on file extension
        # To ensure it's viewed in browser and not downloaded, we use 'inline' disposition
        response = FileResponse(image_obj.file.open(), content_type=image_obj.file.content_type)
        response['Content-Disposition'] = 'inline'
        return response
    except ImageFile.DoesNotExist:
        return JsonResponse({'error': 'Image not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)