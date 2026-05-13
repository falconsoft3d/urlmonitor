from django.apps import AppConfig


class MonitorConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'monitor'
    verbose_name = 'Monitor de URLs'

    def ready(self):
        import os
        # Solo iniciar en el proceso hijo del auto-reloader (evita doble inicio)
        if os.environ.get('RUN_MAIN') == 'true' or not os.environ.get('RUN_MAIN'):
            from . import scheduler
            scheduler.start()
