from django.db import models

class Entry(models.Model):
    title = models.CharField(max_length=255)
    content = models.TextField()
    last_modified_by = models.CharField(max_length=255)
    last_modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

class Edit(models.Model):
    entry = models.ForeignKey(Entry, on_delete=models.CASCADE, related_name='edits')
    content_snapshot = models.TextField()
    modified_by = models.CharField(max_length=255)
    summary = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)