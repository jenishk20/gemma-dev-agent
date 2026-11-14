from django.db import migrations, models
import django.contrib.auth.models

class Migration(migrations.Migration):
    dependencies = []
    operations = [
        migrations.CreateModel(
            name='Secret',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name_null=True)),
                ('secret_text', models.TextField()),
                ('user', models.OneToOneField(on_delete=models.CASCADE, on_delete=models.CASCADE, to=django.contrib.auth.models.User)),
            ],
        ),
    ]