
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('topics', '0006_alter_generationsession_options_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='UserApiKey',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('provider', models.CharField(choices=[('gemini', 'Google Gemini'), ('groq', 'Groq'), ('openrouter', 'OpenRouter')], max_length=20, verbose_name='Провайдер')),
                ('encrypted_key', models.TextField(verbose_name='Зашифрований ключ')),
                ('last4', models.CharField(max_length=4, verbose_name='Останні 4 символи')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Створено')),
                ('last_used_at', models.DateTimeField(blank=True, null=True, verbose_name='Останнє використання')),
                ('is_valid', models.BooleanField(default=True, verbose_name='Дійсний')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='api_keys', to=settings.AUTH_USER_MODEL, verbose_name='Користувач')),
            ],
            options={
                'verbose_name': 'Власний API-ключ',
                'verbose_name_plural': 'Власні API-ключі',
                'ordering': ['-created_at'],
                'constraints': [models.UniqueConstraint(fields=('user', 'provider'), name='unique_user_provider_key')],
            },
        ),
    ]
