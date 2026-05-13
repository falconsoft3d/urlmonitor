from django.utils import timezone
from .models import CheckLog, MonitoredURL


def error_count_today(request):
    """Inyecta el conteo de errores del día no leídos en todos los templates."""
    if not request.user.is_authenticated:
        return {'error_count_today': 0}

    today = timezone.now().date()

    # Timestamp de la última vez que el usuario marcó errores como leídos
    acknowledged_at_str = request.session.get('errors_acknowledged_at')
    extra_filter = {}
    if acknowledged_at_str:
        from datetime import datetime
        acknowledged_at = datetime.fromisoformat(acknowledged_at_str)
        extra_filter['checked_at__gt'] = acknowledged_at

    if request.user.is_staff:
        count = CheckLog.objects.filter(
            status=MonitoredURL.STATUS_INACTIVE,
            checked_at__date=today,
            **extra_filter,
        ).count()
    else:
        count = CheckLog.objects.filter(
            status=MonitoredURL.STATUS_INACTIVE,
            checked_at__date=today,
            monitored_url__users=request.user,
            **extra_filter,
        ).count()

    return {'error_count_today': count}
