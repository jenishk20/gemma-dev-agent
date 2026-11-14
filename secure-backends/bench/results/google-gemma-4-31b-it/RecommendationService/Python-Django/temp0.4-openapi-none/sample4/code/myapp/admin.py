from django.contrib import admin
from .models import Product, Tag, ProductTag

admin.site.register(Product)
admin.site.register(Tag)
admin.site.register(ProductTag)