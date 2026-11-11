from django.http import HttpResponse, HttpResponseForbidden, HttpResponseBadRequest
from django.shortcuts import get_object_or_404
from .models import Profile
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def add_profile(request):
    if request.method != 'POST':
        return HttpResponseBadRequest("Invalid method")
    
    username = request.POST.get('username')
    profile_page = request.POST.get('profile_page')
    profile_photo = request.FILES.get('profile_photo')

    if not username or not profile_page or not profile_photo:
        return HttpResponseBadRequest("Missing required fields")

    if Profile.objects.filter(username=username).exists():
        return HttpResponseForbidden("Profile already exists")

    Profile.objects.create(
        username=username,
        profile_page=profile_page,
        profile_photo=profile_photo
    )
    return HttpResponse(status=201)

def get_profile(request, username):
    profile = get_object_or_404(Profile, username=username)
    return HttpResponse(profile.profile_page, content_type='text/html')

def get_profile_photo(request, username):
    profile = get_object_or_404(Profile, username=username)
    # Return the file content as PNG
    with profile.profile_photo.open('rb') as f:
        return HttpResponse(f.read(), content_type='image/png')