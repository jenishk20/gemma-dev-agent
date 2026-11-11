from django.db import migrations, models

class Migration(migrations.Migration):
    initial_revision = '0001_initial'
    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Product',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=255, unique=True)),
                ('properties', models.JSONField(default=dict)),
            ],
        ),
    ]