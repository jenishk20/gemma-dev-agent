from django.db import migrations, models

class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name='CardAssociation',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name_null=True)),
                ('credit_card', models.CharField(max_length=255)),
                ('phone', models.CharField(max_length=255)),
            ],
            options={
                'unique_together': {('credit_card', 'phone')},
            },
        ),
    ]