from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Profile',
            fields=[
                ('username', models.CharField(max_length=255, primary_key=True, unique=True)),
                ('profile_page_html', models.TextField()),
                ('profile_photo', models.ImageField(upload_to='profiles/')),
            ],
        ),
    ]