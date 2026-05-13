from django.db import models
from django.contrib.auth.models import User


def avatar_upload_path(instance, filename):
    return f'avatars/user_{instance.user.pk}/{filename}'


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField(upload_to=avatar_upload_path, null=True, blank=True)

    def __str__(self):
        return f'Perfil de {self.user.username}'
