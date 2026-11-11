from django.db import models

class Recipe(models.Model):
    title = models.CharField(max_length=255)
    ingredients = models.JSONField()
    instructions = models.TextField()

    def get_avg_rating(self):
        ratings = self.ratings.all()
        if not ratings:
            return None
        return sum([r.rating for r in ratings]) / ratings.count()

class Comment(models.Model):
    recipe = models.ForeignKey(Recipe, related_name='comments', on_delete=models.CASCADE)
    comment = models.TextField()

class Rating(models.Model):
    recipe = models.ForeignKey(Recipe, related_name='ratings', on_delete=models.CASCADE)
    rating = models.IntegerField() # 1 to 5