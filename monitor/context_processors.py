from django.utils import timezone
from .models import CheckLog, MonitoredURL


def error_count_today(request):
    """Inyecta el conteo de errores del día actual en todos los templates."""
    if not request.user.is_authenticated:
        return {'error_count_today': 0}

    today = timezone.now().date()

    if request.user.is_staff:
        count = CheckLog.objects.filter(
            status=MonitoredURL.STATUS_INACTIVE,
            checked_at__date=today,
        ).count()
    else:
        count = CheckLog.objects.filter(
            status=MonitoredURL.STATUS_INACTIVE,
            checked_at__date=today,
            monitored_url__users=request.user,
        ).count()

    return {'error_count_today': count}
