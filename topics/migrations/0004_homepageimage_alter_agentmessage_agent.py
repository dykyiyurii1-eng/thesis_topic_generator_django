from django.db import migrations, models
class Migration(migrations.Migration):
    dependencies = [
        ('topics', '0003_seed_interests_and_quiz'),
    ]
    operations = [
        migrations.CreateModel(
            name='HomePageImage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('image', models.ImageField(upload_to='home_images/', verbose_name='Картинка на головну')),
                ('is_active', models.BooleanField(default=True, verbose_name='Активна')),
            ],
        ),
        migrations.AlterField(
            model_name='agentmessage',
            name='agent',
            field=models.CharField(choices=[('generator', 'Генератор'), ('critic', 'Критик'), ('judge', 'Суддя'), ('user', 'Користувач')], max_length=20, verbose_name='Агент'),
        ),
    ]
