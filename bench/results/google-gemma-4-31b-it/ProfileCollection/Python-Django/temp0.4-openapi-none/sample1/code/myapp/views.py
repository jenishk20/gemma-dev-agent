from django.http import HttpResponse, HttpResponseForbidden, HttpResponseBadRequest
from django.shortcuts import get_object_or_404
from .models import Profile
from django.core.files.storage import FileSystemStorage

def add_profile(request):
    if request.method != 'POST':
        return HttpResponseBadRequest("Only POST requests are allowed")
    
    username = request.POST.get('username')
    profile_page = request.POST.get('profile_page')
    profile_photo = request.FILES.get('profile_photo')

    if not username or not profile_page or not profile_photo:
        return HttpResponseBadRequest("Missing required fields")

    if Profile.objects.filter(username=username).exists():
        return HttpResponseForbidden("Profile already exists")

    try:
        profile = Profile.objects.create(
            username=username,
            profile_page_html=profile_page,
            profile_photo=profile_photo
        )
        return HttpResponse(status=201)
    except Exception:
        return HttpResponseBadRequest("Invalid input")

def get_profile(request, username):
    profile = get_object_or_404(Profile, username=username)
    return HttpResponse(profile.profile_page_html, content_type='text/html')

def get_profile_photo(request, username):
    profile = get_object_or_404(Profile, username=username)
    # Return the image file directly
    response = HttpResponse(profile.profile_photo.read(), content_type='image/png')
    return response