import mimetypes
from django.http import JsonResponse, FileResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from .models import Image

@csrf_exempt
def upload_image(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        if 'file' not in request.FILES:
            return JsonResponse({'error': 'No file provided'}, status=400)
        
        uploaded_file = request.FILES['file']
        
        # Determine mimetype
        content_type, _ = mimetypes.guess_type(uploaded_file.name)
        
        img = Image.objects.create(
            file=uploaded_file,
            content_type=content_type or 'application/octet-stream'
        )
        
        return JsonResponse({'id': str(img.id)}, status=200)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def serve_image(request, imageId):
    try:
        img = Image.objects.get(id=imageId)
        # FileResponse handles the file streaming
        response = FileResponse(img.file.open(), content_type=img.content_type)
        # 'inline' tells the browser to try and render it rather than download it
        response['Content-Disposition'] = f'inline; filename="{img.file.name}"'
        return response
    except Image.DoesNotExist:
        return JsonResponse({'error': 'Image not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)