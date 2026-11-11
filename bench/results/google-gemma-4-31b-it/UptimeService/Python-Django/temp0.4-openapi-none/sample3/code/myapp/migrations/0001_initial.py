from django.db import migrations, models

class Migration(migrations.Migration):
    initial = True
    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Service',
            fields=[
                ('id', models.AutoField(auto_created=True, orphan=False, primary_key=True, serialize=False)),
                ('service_id', models.CharField(max_length=255, unique=True)),
                ('token', models.CharField(max_length=255)),
                ('last_notification', models.DateTimeField(auto_now=True)),
            ],
        ),
    ]