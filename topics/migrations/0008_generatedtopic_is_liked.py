from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('topics', '0007_userapikey'),
    ]

    operations = [
        migrations.AddField(
            model_name='generatedtopic',
            name='is_liked',
            field=models.BooleanField(default=False, verbose_name='Подобається'),
        ),
    ]
