import mimetypes
from django.http import JsonResponse, FileResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from .models import ImageUpload

class UploadImageView(View):
    @csrf_exempt
    def post(self, request):
        try:
            if 'file' not in request.FILES:
                return JsonResponse({'error': 'No file provided'}, status=400)
            
            uploaded_file = request.FILES['file']
            image_obj = ImageUpload.objects.create(file=uploaded_file)
            
            return JsonResponse({'id': str(image_obj.id)}, status=200)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

class ServeImageView(View):
    def get(self, request, imageId):
        try:
            image_obj = ImageUpload.objects.get(id=imageId)
            file_path = image_obj.file.path
            
            # Determine mimetype to ensure browser renders it
            content_type, _ = mimetypes.guess_type(file_path)
            if not content_type:
                content_type = 'application/octet-stream'
            
            # FileResponse handles streaming and we set content_type for browser viewing
            # We avoid 'Content-Disposition: attachment' to prevent forced download
            response = FileResponse(image_obj.file.open(), content_type=content_type)
            response['Content-Disposition'] = 'inline'
            return response
            
        except ImageUpload.DoesNotExist:
            return JsonResponse({'error': 'Image not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)