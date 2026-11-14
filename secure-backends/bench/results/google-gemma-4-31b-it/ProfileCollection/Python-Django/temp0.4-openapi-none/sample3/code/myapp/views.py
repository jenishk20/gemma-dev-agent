from django.http import HttpResponse, HttpResponseForbidden, HttpResponseBadRequest, HttpResponseNotFound
from django.views.decorators.csrf import csrf_exempt
from .models import Profile
import os

@csrf_exempt
def add_profile(request):
    if request.method != 'POST':
        return HttpResponseBadRequest("Only POST allowed")
    
    username = request.POST.get('username')
    profile_page = request.POST.get('profile_page')
    profile_photo = request.FILES.get('profile_photo')

    if not username or not profile_page or not profile_photo:
        return HttpResponseBadRequest("Missing required fields")

    if Profile.objects.filter(username=username).exists():
        return HttpResponseForbidden("Profile already exists")

    try:
        Profile.objects.create(
            username=username,
            profile_page=profile_page,
            profile_photo=profile_photo
        )
        return HttpResponse(status=201)
    except Exception:
        return HttpResponseBadRequest("Invalid input")

def get_profile(request, username):
    try:
        profile = Profile.objects.get(username=username)
        return HttpResponse(profile.profile_page, content_type='text/html')
    except Profile.DoesNotExist:
        return HttpResponseNotFound()

def get_profile_photo(request, username):
    try:
        profile = Profile.objects.get(username=username)
        # Return the binary content of the image
        with profile.profile_photo.open('rb') as f:
            return HttpResponse(f.read(), content_type='image/png')
    except Profile.DoesNotExist:
        return HttpResponseNotFound()