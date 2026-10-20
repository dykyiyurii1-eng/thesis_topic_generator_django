from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class Profile(models.Model):
    ROLE_CHOICES = (
        ('student', 'Студент'),
        ('teacher', 'Викладач'),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='student', verbose_name="Роль")
    faculty = models.CharField(max_length=200, blank=True, verbose_name="Факультет")
    gemini_key = models.CharField(max_length=255, blank=True, null=True, verbose_name="API-ключ Gemini")
    groq_key = models.CharField(max_length=255, blank=True, null=True, verbose_name="API-ключ Groq")
    consent_given_at = models.DateTimeField(null=True, blank=True, verbose_name="Час надання згоди")

    class Meta:
        verbose_name = "Профіль"
        verbose_name_plural = "Профілі"

    def __str__(self):
        return f"Профіль {self.user.username}"

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()