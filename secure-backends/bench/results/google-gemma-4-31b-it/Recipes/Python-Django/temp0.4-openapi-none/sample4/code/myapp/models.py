from django.db import models
from django.db.models import Avg

class Recipe(models.Model):
    title = models.CharField(max_length=255)
    ingredients = models.JSONField() # Stores list of strings
    instructions = models.TextField()

    def get_avg_rating(self):
        avg = Rating.objects.filter(recipe=self).aggregate(Avg('value'))['value__avg']
        return float(avg) if avg is not None else None

class Comment(models.Model):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='comments')
    text = models.TextField()

class Rating(models.Model):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='ratings')
    value = models.IntegerField()