from django.db import models
from django.contrib.auth.models import User


class MonitoredURL(models.Model):
    STATUS_UNKNOWN = 'unknown'
    STATUS_ACTIVE = 'active'
    STATUS_INACTIVE = 'inactive'

    STATUS_CHOICES = [
        (STATUS_UNKNOWN, 'Sin verificar'),
        (STATUS_ACTIVE, 'Activo'),
        (STATUS_INACTIVE, 'Inactivo'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='monitored_urls')
    name = models.CharField(max_length=200, verbose_name='Nombre')
    url = models.URLField(max_length=500, verbose_name='URL')
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_UNKNOWN,
        verbose_name='Estado',
    )
    status_code = models.IntegerField(null=True, blank=True, verbose_name='Código HTTP')
    response_time = models.FloatField(
        null=True, blank=True,
        verbose_name='Tiempo de respuesta (ms)',
    )
    last_checked = models.DateTimeField(null=True, blank=True, verbose_name='Última verificación')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Creado')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Actualizado')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'URL Monitoreada'
        verbose_name_plural = 'URLs Monitoreadas'

    def __str__(self):
        return f'{self.name} ({self.url})'

    @property
    def is_active(self):
        return self.status == self.STATUS_ACTIVE

    @property
    def status_badge_classes(self):
        if self.status == self.STATUS_ACTIVE:
            return 'bg-green-100 text-green-800'
        if self.status == self.STATUS_INACTIVE:
            return 'bg-red-100 text-red-800'
        return 'bg-gray-100 text-gray-600'

    @property
    def status_dot_classes(self):
        if self.status == self.STATUS_ACTIVE:
            return 'bg-green-500'
        if self.status == self.STATUS_INACTIVE:
            return 'bg-red-500'
        return 'bg-gray-400'

    @property
    def status_label(self):
        return dict(self.STATUS_CHOICES).get(self.status, 'Desconocido')
