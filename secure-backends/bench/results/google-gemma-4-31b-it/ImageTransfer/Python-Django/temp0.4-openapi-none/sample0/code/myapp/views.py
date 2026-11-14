from django.http import JsonResponse, FileResponse, HttpResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from .models import ImageUpload
import mimetypes

class UploadImageView(View):
    @csrf_exempt
    def post(self, request):
        try:
            if 'file' not in request.FILES:
                return JsonResponse({'error': 'No file uploaded'}, status=400)
            
            uploaded_file = request.FILES['file']
            # Determine mimetype
            content_type, _ = mimetypes.guess_type(uploaded_file.name)
            if not content_type:
                content_type = uploaded_file.content_type

            image_obj = ImageUpload.objects.create(
                file=uploaded_file,
                content_type=content_type
            )
            
            return JsonResponse({'id': str(image_obj.id)}, status=200)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

class ServeImageView(View):
    def get(self, request, imageId):
        try:
            image_obj = ImageUpload.objects.get(id=imageId)
            # Use FileResponse to serve the file. 
            # content_type ensures browser renders it rather than downloading.
            response = FileResponse(image_obj.file.open(), content_type=image_obj.content_type)
            # Ensure it is viewed in browser (inline)
            response['Content-Disposition'] = 'inline'
            return response
        except ImageUpload.DoesNotExist:
            return JsonResponse({'error': 'Image not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)