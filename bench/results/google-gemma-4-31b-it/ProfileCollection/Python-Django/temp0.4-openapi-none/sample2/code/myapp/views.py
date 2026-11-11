from django.http import HttpResponse, HttpResponseForbidden, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from .models import Profile

@csrf_exempt
def add_profile(request):
    if request.method != 'POST':
        return HttpResponseBadRequest("Invalid method")
    
    try:
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
            profile_photo=profile_photo.read()
        )
        return HttpResponse(status=201)
    except Exception:
        return HttpResponseBadRequest("Invalid input")

def get_profile(request, username):
    try:
        profile = Profile.objects.get(username=username)
        return HttpResponse(profile.profile_page, content_type='text/html')
    except Profile.DoesNotExist:
        return HttpResponse(status=404)

def get_profile_photo(request, username):
    try:
        profile = Profile.objects.get(username=username)
        return HttpResponse(profile.profile_photo, content_type='image/png')
    except Profile.DoesNotExist:
        return HttpResponse(status=404)