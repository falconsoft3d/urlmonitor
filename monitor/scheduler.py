import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)

_scheduler = BackgroundScheduler(timezone='UTC')
JOB_ID = 'auto_check_all_urls'


def _run_check():
    """Verifica todas las URLs del sistema y envía alertas Telegram si detecta caídas."""
    from django.utils import timezone
    from .models import MonitoredURL
    from .views import _do_check

    urls = MonitoredURL.objects.select_related('user').all()
    count = 0
    for url in urls:
        _do_check(url)
        url.last_checked = timezone.now()
        url.save(update_fields=['status', 'status_code', 'response_time', 'last_checked', 'updated_at', 'telegram_alerted'])
        count += 1
    logger.info('Auto-check completado: %d URLs verificadas', count)


def reschedule(interval_minutes, enabled):
    """Reprograma (o cancela) el job según la configuración actual."""
    if _scheduler.get_job(JOB_ID):
        _scheduler.remove_job(JOB_ID)

    if enabled and interval_minutes > 0:
        _scheduler.add_job(
            _run_check,
            trigger=IntervalTrigger(minutes=interval_minutes),
            id=JOB_ID,
            replace_existing=True,
            misfire_grace_time=60,
        )
        logger.info('Auto-check programado cada %d minuto(s)', interval_minutes)
    else:
        logger.info('Auto-check desactivado')


def start():
    """Inicia el scheduler cargando la configuración guardada en BD."""
    try:
        from .models import SiteConfig
        config = SiteConfig.get()
        reschedule(config.check_interval_minutes, config.auto_check_enabled)
        if not _scheduler.running:
            _scheduler.start()
            logger.info('Scheduler iniciado')
    except Exception as exc:
        logger.warning('No se pudo iniciar el scheduler: %s', exc)
