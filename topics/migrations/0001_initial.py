import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
class Migration(migrations.Migration):
    initial = True
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.CreateModel(
            name='Profile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(choices=[('student', 'Студент'), ('teacher', 'Викладач')], default='student', max_length=10, verbose_name='Роль')),
                ('faculty', models.CharField(blank=True, max_length=200, verbose_name='Факультет')),
                ('gemini_key', models.CharField(blank=True, max_length=255, null=True, verbose_name='API-ключ Gemini')),
                ('groq_key', models.CharField(blank=True, max_length=255, null=True, verbose_name='API-ключ Groq')),
                ('consent_given_at', models.DateTimeField(blank=True, null=True, verbose_name='Час надання згоди')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='profile', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Профіль',
                'verbose_name_plural': 'Профілі',
            },
        ),
    ]
