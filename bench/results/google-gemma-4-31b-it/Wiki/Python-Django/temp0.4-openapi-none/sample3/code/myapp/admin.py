from django.contrib import admin
from .models import WikiEntry, WikiEdit

admin.site.register(WikiEntry)
admin.site.register(WikiEdit)