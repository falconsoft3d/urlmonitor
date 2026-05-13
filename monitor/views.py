import requests as http_requests
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse

from django.core.paginator import Paginator
from .models import MonitoredURL, CheckLog, SiteConfig
from .forms import MonitoredURLForm, ScheduleConfigForm, TelegramConfigForm, RegistrationConfigForm

# URLs destino seguras para el parámetro "next"
SAFE_NEXT_URLS = {'url_list', 'dashboard'}


def home(request):
    return render(request, 'home.html')


@login_required
def dashboard(request):
    urls = MonitoredURL.objects.filter(user=request.user)
    total = urls.count()
    active = urls.filter(status=MonitoredURL.STATUS_ACTIVE).count()
    inactive = urls.filter(status=MonitoredURL.STATUS_INACTIVE).count()
    unknown = urls.filter(status=MonitoredURL.STATUS_UNKNOWN).count()
    recent_urls = urls[:6]

    context = {
        'total': total,
        'active': active,
        'inactive': inactive,
        'unknown': unknown,
        'recent_urls': recent_urls,
    }
    return render(request, 'monitor/dashboard.html', context)


@login_required
def url_list(request):
    urls = MonitoredURL.objects.filter(user=request.user)
    return render(request, 'monitor/url_list.html', {'urls': urls})


@login_required
def url_add(request):
    if request.method == 'POST':
        form = MonitoredURLForm(request.POST)
        if form.is_valid():
            monitored_url = form.save(commit=False)
            monitored_url.user = request.user
            monitored_url.save()
            messages.success(request, f'URL "{monitored_url.name}" agregada exitosamente.')
            return redirect('url_list')
    else:
        form = MonitoredURLForm()

    return render(request, 'monitor/url_form.html', {'form': form, 'action': 'Agregar'})


@login_required
def url_edit(request, pk):
    monitored_url = get_object_or_404(MonitoredURL, pk=pk, user=request.user)

    if request.method == 'POST':
        form = MonitoredURLForm(request.POST, instance=monitored_url)
        if form.is_valid():
            form.save()
            messages.success(request, f'URL "{monitored_url.name}" actualizada exitosamente.')
            return redirect('url_list')
    else:
        form = MonitoredURLForm(instance=monitored_url)

    return render(request, 'monitor/url_form.html', {
        'form': form,
        'action': 'Editar',
        'monitored_url': monitored_url,
    })


@login_required
def url_delete(request, pk):
    monitored_url = get_object_or_404(MonitoredURL, pk=pk, user=request.user)

    if request.method == 'POST':
        name = monitored_url.name
        monitored_url.delete()
        messages.success(request, f'URL "{name}" eliminada exitosamente.')
        return redirect('url_list')

    return render(request, 'monitor/url_confirm_delete.html', {'monitored_url': monitored_url})


def _send_telegram_alert(monitored_url):
    """Envía notificación Telegram cuando una URL cae."""
    try:
        config = SiteConfig.get()
        if not config.telegram_enabled or not config.telegram_bot_token or not config.telegram_chat_id:
            return
        text = (
            f"⛔ *URL Caída*\n\n"
            f"*{monitored_url.name}*\n"
            f"`{monitored_url.url}`\n\n"
            f"Código HTTP: `{monitored_url.status_code or 'Sin respuesta'}`"
        )
        http_requests.post(
            f'https://api.telegram.org/bot{config.telegram_bot_token}/sendMessage',
            json={'chat_id': config.telegram_chat_id, 'text': text, 'parse_mode': 'Markdown'},
            timeout=5,
        )
    except Exception:
        pass


def _do_check(monitored_url):
    """Realiza la verificación HTTP de una URL, actualiza el objeto y guarda un CheckLog."""
    previous_status = monitored_url.status
    success, detail = False, 'Error'

    try:
        response = http_requests.get(
            monitored_url.url,
            timeout=10,
            allow_redirects=True,
            headers={'User-Agent': 'URLMonitor/1.0'},
        )
        monitored_url.status_code = response.status_code
        monitored_url.response_time = round(response.elapsed.total_seconds() * 1000, 1)
        monitored_url.status = (
            MonitoredURL.STATUS_ACTIVE
            if response.status_code < 400
            else MonitoredURL.STATUS_INACTIVE
        )
        CheckLog.objects.create(
            monitored_url=monitored_url,
            status=monitored_url.status,
            status_code=monitored_url.status_code,
            response_time=monitored_url.response_time,
        )
        success, detail = True, response.status_code
    except http_requests.exceptions.RequestException as exc:
        monitored_url.status = MonitoredURL.STATUS_INACTIVE
        monitored_url.status_code = None
        monitored_url.response_time = None
        error_name = type(exc).__name__
        CheckLog.objects.create(
            monitored_url=monitored_url,
            status=MonitoredURL.STATUS_INACTIVE,
            error=error_name,
        )
        success, detail = False, error_name

    # Notificar por Telegram solo en la primera caída (no spamear si sigue caída)
    if monitored_url.status == MonitoredURL.STATUS_INACTIVE:
        if not monitored_url.telegram_alerted:
            _send_telegram_alert(monitored_url)
            monitored_url.telegram_alerted = True
    else:
        # URL volvió a funcionar → resetear para que la próxima caída sí notifique
        monitored_url.telegram_alerted = False

    return success, detail


@login_required
def url_check(request, pk):
    monitored_url = get_object_or_404(MonitoredURL, pk=pk, user=request.user)
    success, detail = _do_check(monitored_url)
    monitored_url.last_checked = timezone.now()
    monitored_url.save()

    if success:
        messages.success(
            request,
            f'"{monitored_url.name}": código {detail} — {monitored_url.status_label}',
        )
    else:
        messages.error(request, f'"{monitored_url.name}": sin conexión ({detail})')

    next_url = request.GET.get('next', 'url_list')
    if next_url not in SAFE_NEXT_URLS:
        next_url = 'url_list'
    return redirect(next_url)


@login_required
def url_check_all(request):
    urls = MonitoredURL.objects.filter(user=request.user)
    checked = 0

    for monitored_url in urls:
        _do_check(monitored_url)
        monitored_url.last_checked = timezone.now()
        monitored_url.save()
        checked += 1

    messages.success(request, f'Se verificaron {checked} URL{"s" if checked != 1 else ""} exitosamente.')
    return redirect('dashboard')


@login_required
def log_list(request):
    qs = CheckLog.objects.filter(monitored_url__user=request.user).select_related('monitored_url')
    paginator = Paginator(qs, 40)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    return render(request, 'monitor/log_list.html', {
        'page_obj': page_obj,
        'total': paginator.count,
    })


def _staff_required(user):
    return user.is_active and user.is_staff


@login_required
def url_detail(request, pk):
    from django.db.models import Avg, Count, Q
    monitored_url = get_object_or_404(MonitoredURL, pk=pk, user=request.user)
    all_logs = monitored_url.logs.all()
    logs = all_logs[:50]

    total_checks = all_logs.count()
    total_ok = all_logs.filter(status=MonitoredURL.STATUS_ACTIVE).count()
    total_fail = all_logs.filter(status=MonitoredURL.STATUS_INACTIVE).count()
    uptime_pct = round(total_ok / total_checks * 100, 1) if total_checks else None
    avg_response = all_logs.filter(response_time__isnull=False).aggregate(v=Avg('response_time'))['v']
    avg_response = round(avg_response, 1) if avg_response else None

    # Últimas 5 caídas con fecha
    last_failures = all_logs.filter(
        status=MonitoredURL.STATUS_INACTIVE
    ).order_by('-checked_at')[:5]

    form = MonitoredURLForm(instance=monitored_url)
    return render(request, 'monitor/url_detail.html', {
        'monitored_url': monitored_url,
        'logs': logs,
        'form': form,
        'total_checks': total_checks,
        'total_ok': total_ok,
        'total_fail': total_fail,
        'uptime_pct': uptime_pct,
        'avg_response': avg_response,
        'last_failures': last_failures,
    })


@login_required
@user_passes_test(_staff_required)
def config_schedule(request):
    from . import scheduler as _scheduler_module
    config = SiteConfig.get()
    if request.method == 'POST':
        form = ScheduleConfigForm(request.POST, instance=config)
        if form.is_valid():
            form.save()
            _scheduler_module.reschedule(config.check_interval_minutes, config.auto_check_enabled)
            messages.success(request, 'Configuración de verificación automática guardada.')
            return redirect('config_schedule')
    else:
        form = ScheduleConfigForm(instance=config)
    return render(request, 'monitor/config_schedule.html', {'form': form, 'config': config})


@login_required
@user_passes_test(_staff_required)
def config_telegram(request):
    config = SiteConfig.get()
    if request.method == 'POST':
        form = TelegramConfigForm(request.POST, instance=config)
        if form.is_valid():
            form.save()
            messages.success(request, 'Configuración de Telegram guardada.')
            return redirect('config_telegram')
    else:
        form = TelegramConfigForm(instance=config)
    return render(request, 'monitor/config_telegram.html', {'form': form, 'config': config})


@login_required
@user_passes_test(_staff_required)
def config_users(request):
    config = SiteConfig.get()
    if request.method == 'POST':
        form = RegistrationConfigForm(request.POST, instance=config)
        if form.is_valid():
            form.save()
            messages.success(request, 'Configuración de usuarios guardada.')
            return redirect('config_users')
    else:
        form = RegistrationConfigForm(instance=config)
    return render(request, 'monitor/config_users.html', {'form': form, 'config': config})


@login_required
def scheduler_status(request):
    """Devuelve JSON con el estado del scheduler para el widget del sidebar."""
    from . import scheduler as _sched
    config = SiteConfig.get()

    if not config.auto_check_enabled:
        return JsonResponse({'enabled': False})

    job = _sched._scheduler.get_job(_sched.JOB_ID)
    if job is None:
        return JsonResponse({'enabled': False})

    import datetime
    next_run = job.next_run_time          # datetime aware UTC
    now = timezone.now()
    seconds_remaining = max(0, int((next_run - now).total_seconds()))

    return JsonResponse({
        'enabled': True,
        'interval_minutes': config.check_interval_minutes,
        'seconds_remaining': seconds_remaining,
        'next_run': next_run.isoformat(),
    })


@login_required
def url_toggle_public(request, pk):
    """Activa/desactiva la página pública de una URL."""
    if request.method != 'POST':
        return redirect('url_detail', pk=pk)
    monitored_url = get_object_or_404(MonitoredURL, pk=pk, user=request.user)
    monitored_url.is_public = not monitored_url.is_public
    monitored_url.save(update_fields=['is_public'])
    state = 'activado' if monitored_url.is_public else 'desactivado'
    messages.success(request, f'Acceso público {state}.')
    return redirect('url_detail', pk=pk)


def url_public(request, token):
    """Página pública sin login — para compartir con clientes."""
    from django.db.models import Avg
    monitored_url = get_object_or_404(MonitoredURL, public_token=token, is_public=True)
    all_logs = monitored_url.logs.all()

    total_checks = all_logs.count()
    total_ok = all_logs.filter(status=MonitoredURL.STATUS_ACTIVE).count()
    total_fail = all_logs.filter(status=MonitoredURL.STATUS_INACTIVE).count()
    uptime_pct = round(total_ok / total_checks * 100, 1) if total_checks else None
    avg_response = all_logs.filter(response_time__isnull=False).aggregate(v=Avg('response_time'))['v']
    avg_response = round(avg_response, 1) if avg_response else None
    last_failures = all_logs.filter(status=MonitoredURL.STATUS_INACTIVE).order_by('-checked_at')[:10]
    recent_logs = all_logs[:30]

    return render(request, 'monitor/url_public.html', {
        'monitored_url': monitored_url,
        'total_checks': total_checks,
        'total_ok': total_ok,
        'total_fail': total_fail,
        'uptime_pct': uptime_pct,
        'avg_response': avg_response,
        'last_failures': last_failures,
        'recent_logs': recent_logs,
    })
