import requests as http_requests
from django.db import models
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse

from django.core.paginator import Paginator
from .models import MonitoredURL, CheckLog, SiteConfig
from .forms import MonitoredURLForm, MonitoredURLAdminForm, ScheduleConfigForm, TelegramConfigForm, RegistrationConfigForm

# URLs destino seguras para el parámetro "next"
SAFE_NEXT_URLS = {'url_list', 'dashboard'}


def _url_qs(request):
    """Devuelve todas las URLs si el usuario es staff, solo las asignadas al usuario si no lo es."""
    if request.user.is_staff:
        return MonitoredURL.objects.all()
    return MonitoredURL.objects.filter(users=request.user)


def _get_url_or_404(pk, request):
    """Recupera una MonitoredURL; staff puede acceder a cualquiera, el resto solo a las suyas."""
    if request.user.is_staff:
        return get_object_or_404(MonitoredURL, pk=pk)
    return get_object_or_404(MonitoredURL, pk=pk, users=request.user)


def home(request):
    return render(request, 'home.html')


@login_required
def dashboard(request):
    urls = _url_qs(request)
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
    urls = _url_qs(request)
    status_filter = request.GET.get('status')
    search_query = request.GET.get('q', '').strip()
    valid_statuses = {MonitoredURL.STATUS_ACTIVE, MonitoredURL.STATUS_INACTIVE, MonitoredURL.STATUS_UNKNOWN}
    if status_filter in valid_statuses:
        urls = urls.filter(status=status_filter)
    if search_query:
        urls = urls.filter(
            models.Q(name__icontains=search_query) | models.Q(url__icontains=search_query)
        )
    return render(request, 'monitor/url_list.html', {
        'urls': urls,
        'status_filter': status_filter,
        'search_query': search_query,
    })


@login_required
def url_add(request):
    FormClass = MonitoredURLAdminForm if request.user.is_staff else MonitoredURLForm
    if request.method == 'POST':
        form = FormClass(request.POST)
        if form.is_valid():
            monitored_url = form.save(commit=False)
            monitored_url.save()
            if not request.user.is_staff:
                # usuario normal: se asigna a sí mismo
                monitored_url.users.add(request.user)
            else:
                # admin: guarda la M2M seleccionada en el form
                form.save_m2m()
            messages.success(request, f'URL "{monitored_url.name}" agregada exitosamente.')
            return redirect('url_list')
    else:
        form = FormClass()

    return render(request, 'monitor/url_form.html', {'form': form, 'action': 'Agregar'})


@login_required
def url_edit(request, pk):
    monitored_url = _get_url_or_404(pk, request)
    FormClass = MonitoredURLAdminForm if request.user.is_staff else MonitoredURLForm

    if request.method == 'POST':
        form = FormClass(request.POST, instance=monitored_url)
        if form.is_valid():
            form.save()
            messages.success(request, f'URL "{monitored_url.name}" actualizada exitosamente.')
            return redirect('url_list')
    else:
        form = FormClass(instance=monitored_url)

    return render(request, 'monitor/url_form.html', {
        'form': form,
        'action': 'Editar',
        'monitored_url': monitored_url,
    })


@login_required
def url_delete(request, pk):
    monitored_url = _get_url_or_404(pk, request)

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


def _do_check(monitored_url, force_notify=False):
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
    # Excepción: verificación manual (force_notify=True) siempre notifica si hay error
    if monitored_url.status == MonitoredURL.STATUS_INACTIVE:
        if force_notify or not monitored_url.telegram_alerted:
            _send_telegram_alert(monitored_url)
            monitored_url.telegram_alerted = True
    else:
        # URL volvió a funcionar → resetear para que la próxima caída sí notifique
        monitored_url.telegram_alerted = False

    return success, detail


@login_required
def url_check(request, pk):
    monitored_url = _get_url_or_404(pk, request)
    success, detail = _do_check(monitored_url, force_notify=True)
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
    urls = _url_qs(request)
    checked = 0

    for monitored_url in urls:
        _do_check(monitored_url)
        monitored_url.last_checked = timezone.now()
        monitored_url.save()
        checked += 1

    messages.success(request, f'Se verificaron {checked} URL{"s" if checked != 1 else ""} exitosamente.')
    return redirect('dashboard')


@login_required
def url_check_ajax(request, pk):
    """Verifica una URL y devuelve el resultado en JSON (para Verificar todas animado)."""
    if request.method != 'POST':
        return JsonResponse({'ok': False}, status=405)
    monitored_url = _get_url_or_404(pk, request)
    success, detail = _do_check(monitored_url)
    monitored_url.last_checked = timezone.now()
    monitored_url.save()
    return JsonResponse({
        'ok': success,
        'status': monitored_url.status,
        'status_code': monitored_url.status_code,
        'response_time': monitored_url.response_time,
        'status_label': monitored_url.status_label,
    })


@login_required
def log_list(request):
    if request.user.is_staff:
        qs = CheckLog.objects.all().select_related('monitored_url')
    else:
        qs = CheckLog.objects.filter(monitored_url__users=request.user).select_related('monitored_url')
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
    monitored_url = _get_url_or_404(pk, request)
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

    # Tiempo activo sin caídas (desde la última caída o desde el primer check)
    uptime_since = None
    uptime_label = None
    last_failure = all_logs.filter(status=MonitoredURL.STATUS_INACTIVE).order_by('-checked_at').first()
    first_ok = all_logs.filter(status=MonitoredURL.STATUS_ACTIVE).order_by('checked_at').first()
    reference = None
    if last_failure:
        # Busca el primer check exitoso DESPUÉS de la última caída
        ok_after = all_logs.filter(
            status=MonitoredURL.STATUS_ACTIVE,
            checked_at__gt=last_failure.checked_at
        ).order_by('checked_at').first()
        reference = ok_after.checked_at if ok_after else None
    elif first_ok:
        reference = first_ok.checked_at

    if reference:
        delta = timezone.now() - reference
        total_seconds = int(delta.total_seconds())
        days = delta.days
        hours = (total_seconds % 86400) // 3600
        minutes = (total_seconds % 3600) // 60
        if days >= 1:
            uptime_label = f'{days} día{"s" if days != 1 else ""} y {hours} hora{"s" if hours != 1 else ""}'
        elif hours >= 1:
            uptime_label = f'{hours} hora{"s" if hours != 1 else ""} y {minutes} minuto{"s" if minutes != 1 else ""}'
        else:
            uptime_label = f'{minutes} minuto{"s" if minutes != 1 else ""}'

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
        'uptime_label': uptime_label,
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
def telegram_test(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Método no permitido'}, status=405)
    config = SiteConfig.get()
    token = config.telegram_bot_token
    chat_id = config.telegram_chat_id
    if not token or not chat_id:
        return JsonResponse({'ok': False, 'error': 'Configura el token y el chat ID primero.'})
    try:
        resp = http_requests.post(
            f'https://api.telegram.org/bot{token}/sendMessage',
            json={'chat_id': chat_id, 'text': '✅ URLMonitor: mensaje de prueba. ¡Telegram funciona correctamente!'},
            timeout=10,
        )
        data = resp.json()
        if data.get('ok'):
            return JsonResponse({'ok': True})
        return JsonResponse({'ok': False, 'error': data.get('description', 'Error desconocido')})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)})


@login_required
@user_passes_test(_staff_required)
def telegram_get_updates(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Método no permitido'}, status=405)
    config = SiteConfig.get()
    token = config.telegram_bot_token
    if not token:
        return JsonResponse({'ok': False, 'error': 'Configura el token primero y guarda.'})
    try:
        resp = http_requests.get(
            f'https://api.telegram.org/bot{token}/getUpdates',
            timeout=10,
        )
        data = resp.json()
        if not data.get('ok'):
            return JsonResponse({'ok': False, 'error': data.get('description', 'Error desconocido')})
        chats = {}
        for update in data.get('result', []):
            for key in ('message', 'channel_post', 'my_chat_member'):
                chat = (update.get(key) or {}).get('chat')
                if chat:
                    chat_id = chat['id']
                    title = chat.get('title') or chat.get('username') or chat.get('first_name') or str(chat_id)
                    chats[chat_id] = {'id': chat_id, 'title': title, 'type': chat.get('type', '')}
        return JsonResponse({'ok': True, 'chats': list(chats.values())})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)})


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
    monitored_url = _get_url_or_404(pk, request)
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

    # Tiempo activo sin caídas
    uptime_label = None
    last_failure = all_logs.filter(status=MonitoredURL.STATUS_INACTIVE).order_by('-checked_at').first()
    first_ok = all_logs.filter(status=MonitoredURL.STATUS_ACTIVE).order_by('checked_at').first()
    reference = None
    if last_failure:
        ok_after = all_logs.filter(
            status=MonitoredURL.STATUS_ACTIVE,
            checked_at__gt=last_failure.checked_at
        ).order_by('checked_at').first()
        reference = ok_after.checked_at if ok_after else None
    elif first_ok:
        reference = first_ok.checked_at

    if reference:
        delta = timezone.now() - reference
        total_seconds = int(delta.total_seconds())
        days = delta.days
        hours = (total_seconds % 86400) // 3600
        minutes = (total_seconds % 3600) // 60
        if days >= 1:
            uptime_label = f'{days} día{"s" if days != 1 else ""} y {hours} hora{"s" if hours != 1 else ""}'
        elif hours >= 1:
            uptime_label = f'{hours} hora{"s" if hours != 1 else ""} y {minutes} minuto{"s" if minutes != 1 else ""}'
        else:
            uptime_label = f'{minutes} minuto{"s" if minutes != 1 else ""}'

    return render(request, 'monitor/url_public.html', {
        'monitored_url': monitored_url,
        'total_checks': total_checks,
        'total_ok': total_ok,
        'total_fail': total_fail,
        'uptime_pct': uptime_pct,
        'avg_response': avg_response,
        'last_failures': last_failures,
        'recent_logs': recent_logs,
        'uptime_label': uptime_label,
    })


# ---------------------------------------------------------------------------
# Análisis técnico de una URL
# ---------------------------------------------------------------------------

def _detect_technologies(headers, html_content):
    """Detecta tecnologías a partir de cabeceras HTTP y contenido HTML."""
    techs = []

    server = headers.get('Server', '')
    powered_by = headers.get('X-Powered-By', '')

    if server:
        techs.append({'name': server, 'category': 'Servidor'})
    if powered_by:
        techs.append({'name': powered_by, 'category': 'Backend'})

    patterns = [
        ('WordPress',   'CMS',       ['/wp-content/', '/wp-includes/', 'wp-json']),
        ('Joomla',      'CMS',       ['/components/com_', 'Joomla!']),
        ('Drupal',      'CMS',       ['Drupal.settings', '/sites/default/files/']),
        ('Shopify',     'E-commerce',['cdn.shopify.com', 'Shopify.theme']),
        ('Wix',         'Website builder', ['static.wixstatic.com', 'wix.com']),
        ('Squarespace', 'Website builder', ['squarespace.com', 'static1.squarespace']),
        ('React',       'JavaScript',['react.js', 'react.min.js', 'react-dom', '__REACT']),
        ('Vue.js',      'JavaScript',['vue.js', 'vue.min.js', 'Vue.config']),
        ('Angular',     'JavaScript',['angular.js', 'ng-version', 'ng-app']),
        ('Next.js',     'JavaScript',['_next/static', '__NEXT_DATA__']),
        ('Nuxt.js',     'JavaScript',['_nuxt/', '__NUXT__']),
        ('jQuery',      'JavaScript',['jquery.min.js', 'jquery.js']),
        ('Bootstrap',   'CSS',       ['bootstrap.min.css', 'bootstrap.css', 'bootstrap.min.js']),
        ('Tailwind CSS','CSS',       ['tailwind', 'cdn.tailwindcss.com']),
        ('Laravel',     'Backend',   ['laravel_session', 'Laravel']),
        ('Django',      'Backend',   ['csrfmiddlewaretoken', 'django']),
        ('Ruby on Rails','Backend',  ['rails', '__rails_assets']),
        ('ASP.NET',     'Backend',   ['__VIEWSTATE', 'asp.net', 'aspnet']),
        ('PHP',         'Backend',   ['.php', 'PHPSESSID']),
        ('Google Analytics','Analytics',['google-analytics.com', 'gtag(', 'ga(']),
        ('Google Tag Manager','Analytics',['googletagmanager.com']),
        ('Cloudflare',  'CDN / Seguridad', ['cloudflare', '__cfuid', '__cf_bm']),
        ('Nginx',       'Servidor',  ['nginx']),
        ('Apache',      'Servidor',  ['Apache']),
        ('Vercel',      'Hosting',   ['vercel', 'x-vercel']),
        ('Netlify',     'Hosting',   ['netlify']),
    ]

    found_names = {t['name'] for t in techs}
    combined = html_content + ' '.join(f'{k}: {v}' for k, v in headers.items())

    for name, category, signals in patterns:
        if name in found_names:
            continue
        if any(sig.lower() in combined.lower() for sig in signals):
            techs.append({'name': name, 'category': category})
            found_names.add(name)

    return techs


def _get_resource_size(url, session, timeout=3):
    """Intenta obtener el tamaño de un recurso via HEAD (fallback: 0)."""
    try:
        r = session.head(url, timeout=timeout, allow_redirects=True)
        cl = r.headers.get('Content-Length')
        if cl and cl.isdigit():
            return int(cl)
    except Exception:
        pass
    return 0


@login_required
def url_analyze(request, pk):
    """Analiza técnicamente una URL: tecnologías, recursos, tiempos, cabeceras de seguridad."""
    from html.parser import HTMLParser
    from urllib.parse import urljoin, urlparse
    import time

    monitored_url = _get_url_or_404(pk, request)
    error = None
    context = {'monitored_url': monitored_url, 'error': None}

    try:
        session = http_requests.Session()
        session.headers.update({'User-Agent': 'URLMonitor-Analyzer/1.0'})

        t0 = time.time()
        response = session.get(monitored_url.url, timeout=15, allow_redirects=True)
        load_time_ms = round((time.time() - t0) * 1000, 1)

        html_content = response.text
        resp_headers = dict(response.headers)
        status_code = response.status_code
        final_url = response.url
        content_length = len(response.content)
        content_type = resp_headers.get('Content-Type', '')
        redirects = len(response.history)

        # --- Tecnologías ---
        technologies = _detect_technologies(resp_headers, html_content)

        # --- Parsear recursos del HTML ---
        class ResourceParser(HTMLParser):
            def __init__(self):
                super().__init__()
                self.resources = []

            def handle_starttag(self, tag, attrs):
                attrs_dict = dict(attrs)
                if tag == 'script' and attrs_dict.get('src'):
                    self.resources.append(('JS', attrs_dict['src']))
                elif tag == 'link' and attrs_dict.get('rel') in (['stylesheet'], 'stylesheet'):
                    href = attrs_dict.get('href', '')
                    if href:
                        self.resources.append(('CSS', href))
                elif tag == 'link' and 'stylesheet' in attrs_dict.get('rel', ''):
                    href = attrs_dict.get('href', '')
                    if href:
                        self.resources.append(('CSS', href))
                elif tag == 'img' and attrs_dict.get('src'):
                    src = attrs_dict['src']
                    if not src.startswith('data:'):
                        self.resources.append(('IMG', src))

        parser = ResourceParser()
        parser.feed(html_content)

        base = final_url
        resources_with_size = []
        seen = set()
        for rtype, rurl in parser.resources[:40]:  # límite 40 para no tardar demasiado
            abs_url = urljoin(base, rurl)
            if abs_url in seen:
                continue
            seen.add(abs_url)
            size = _get_resource_size(abs_url, session)
            resources_with_size.append({
                'type': rtype,
                'url': abs_url,
                'display_url': abs_url if len(abs_url) < 80 else abs_url[:77] + '…',
                'size': size,
                'size_kb': round(size / 1024, 1) if size else 0,
            })

        resources_sorted = sorted(resources_with_size, key=lambda r: r['size'], reverse=True)

        total_resources_size = sum(r['size'] for r in resources_sorted)
        js_count = sum(1 for r in resources_sorted if r['type'] == 'JS')
        css_count = sum(1 for r in resources_sorted if r['type'] == 'CSS')
        img_count = sum(1 for r in resources_sorted if r['type'] == 'IMG')

        # --- Cabeceras de seguridad ---
        security_headers = [
            ('Strict-Transport-Security', 'HSTS', 'Fuerza HTTPS en el navegador.'),
            ('Content-Security-Policy', 'CSP', 'Previene XSS y otros ataques de inyección.'),
            ('X-Frame-Options', 'Clickjacking', 'Evita que la página sea embebida en iframes.'),
            ('X-Content-Type-Options', 'MIME Sniffing', 'Evita que el navegador adivine el tipo de contenido.'),
            ('Referrer-Policy', 'Referrer', 'Controla la información enviada en el encabezado Referer.'),
            ('Permissions-Policy', 'Permisos', 'Restringe el acceso a APIs del navegador.'),
        ]
        security_results = []
        for header, label, description in security_headers:
            present = header.lower() in {k.lower() for k in resp_headers}
            security_results.append({
                'header': header,
                'label': label,
                'description': description,
                'present': present,
                'value': resp_headers.get(header, ''),
            })

        security_score = sum(1 for s in security_results if s['present'])

        # --- Cabeceras generales relevantes ---
        interesting_headers = [
            'Server', 'X-Powered-By', 'Content-Type', 'Cache-Control',
            'Expires', 'Last-Modified', 'ETag', 'Via', 'X-Cache',
            'CF-Ray', 'X-Varnish', 'Access-Control-Allow-Origin',
        ]
        displayed_headers = [
            {'name': h, 'value': resp_headers[h]}
            for h in interesting_headers if h in resp_headers
        ]

        context.update({
            'load_time_ms': load_time_ms,
            'status_code': status_code,
            'final_url': final_url,
            'content_length_kb': round(content_length / 1024, 1),
            'content_type': content_type,
            'redirects': redirects,
            'technologies': technologies,
            'resources': resources_sorted,
            'total_resources': len(resources_sorted),
            'total_resources_size_kb': round(total_resources_size / 1024, 1),
            'js_count': js_count,
            'css_count': css_count,
            'img_count': img_count,
            'security_results': security_results,
            'security_score': security_score,
            'security_total': len(security_results),
            'displayed_headers': displayed_headers,
        })

    except http_requests.exceptions.Timeout:
        context['error'] = 'La solicitud tardó demasiado (timeout).'
    except http_requests.exceptions.ConnectionError:
        context['error'] = 'No se pudo conectar a la URL.'
    except Exception as exc:
        context['error'] = f'Error inesperado: {exc}'

    return render(request, 'monitor/url_analyze.html', context)

