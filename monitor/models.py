from django.db import models
from django.contrib.auth.models import User
import uuid


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
    public_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    is_public = models.BooleanField(default=False, verbose_name='Página pública activa')

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


class CheckLog(models.Model):
    monitored_url = models.ForeignKey(
        MonitoredURL, on_delete=models.CASCADE, related_name='logs', verbose_name='URL'
    )
    checked_at = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de verificación')
    status = models.CharField(max_length=20, verbose_name='Estado')
    status_code = models.IntegerField(null=True, blank=True, verbose_name='Código HTTP')
    response_time = models.FloatField(null=True, blank=True, verbose_name='Tiempo de respuesta (ms)')
    error = models.CharField(max_length=200, blank=True, default='', verbose_name='Error')

    class Meta:
        ordering = ['-checked_at']
        verbose_name = 'Log de verificación'
        verbose_name_plural = 'Logs de verificación'

    def __str__(self):
        return f'{self.monitored_url.name} — {self.checked_at:%Y-%m-%d %H:%M}'

    @property
    def status_badge_classes(self):
        if self.status == MonitoredURL.STATUS_ACTIVE:
            return 'bg-green-100 text-green-800'
        if self.status == MonitoredURL.STATUS_INACTIVE:
            return 'bg-red-100 text-red-800'
        return 'bg-gray-100 text-gray-600'

    @property
    def status_label(self):
        if self.status == MonitoredURL.STATUS_ACTIVE:
            return 'Activo'
        if self.status == MonitoredURL.STATUS_INACTIVE:
            return 'Inactivo'
        return 'Sin verificar'


class SiteConfig(models.Model):
    INTERVAL_CHOICES = [
        (5,    'Cada 5 minutos'),
        (10,   'Cada 10 minutos'),
        (15,   'Cada 15 minutos'),
        (30,   'Cada 30 minutos'),
        (60,   'Cada hora'),
        (120,  'Cada 2 horas'),
        (360,  'Cada 6 horas'),
        (720,  'Cada 12 horas'),
        (1440, 'Cada 24 horas'),
    ]

    check_interval_minutes = models.IntegerField(
        default=60,
        choices=INTERVAL_CHOICES,
        verbose_name='Intervalo de verificación automática',
    )
    auto_check_enabled = models.BooleanField(default=False, verbose_name='Verificación automática activa')
    telegram_bot_token = models.CharField(max_length=300, blank=True, default='', verbose_name='Token del bot')
    telegram_chat_id = models.CharField(max_length=100, blank=True, default='', verbose_name='ID del grupo/chat')
    telegram_enabled = models.BooleanField(default=False, verbose_name='Notificaciones Telegram activas')

    class Meta:
        verbose_name = 'Configuración del sitio'

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return 'Configuración del sitio'
