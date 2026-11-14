from django.db import migrations, models

class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name='Entry',
            fields=[
                ('id', models.BigAutoField(primary_key=True)),
                ('title', models.CharField(max_length=255)),
                ('content', models.TextField()),
                ('last_modified_by', models.CharField(max_length=255)),
                ('last_modified_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='Edit',
            fields=[
                ('id', models.BigAutoField(primary_key=True)),
                ('entry', models.ForeignKey(Entry, on_delete=models.CASCADE)),
                ('content_snapshot', models.TextField()),
                ('modified_by', models.CharField(max_length=255)),
                ('summary', models.CharField(max_length=255)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
            ],
        ),
    ]