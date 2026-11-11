from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden, HttpResponseNotFound
from django.views.decorators.csrf import csrf_exempt
from .models import Profile

@csrf_exempt
def add_profile(request):
    if request.method != 'POST':
        return HttpResponseBadRequest("Only POST allowed")
    
    try:
        username = request.POST.get('username')
        profile_page = request.POST.get('profile_page')
        profile_photo = request.FILES.get('profile_photo')

        if not username or not profile_page or not profile_photo:
            return HttpResponseBadRequest("Missing required fields")

        if Profile.objects.filter(username=username).exists():
            return HttpResponseForbidden("Profile already exists")

        # Read the binary content of the image
        photo_content = profile_photo.read()
        
        Profile.objects.create(
            username=username,
            profile_page=profile_page,
            profile_photo=photo_content
        )
        return HttpResponse("Profile created successfully", status=201)
    except Exception as e:
        return HttpResponseBadRequest(str(e))

def get_profile(request, username):
    try:
        profile = Profile.objects.get(username=username)
        return HttpResponse(profile.profile_page, content_type="text/html")
    except Profile.DoesNotExist:
        return HttpResponseNotFound("Profile not found")

def get_profile_photo(request, username):
    try:
        profile = Profile.objects.get(username=username)
        return HttpResponse(profile.profile_photo, content_type="image/png")
    except Profile.DoesNotExist:
        return HttpResponseNotFound("Photo not found")