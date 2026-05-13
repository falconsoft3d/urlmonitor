import requests as http_requests
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone

from .models import MonitoredURL
from .forms import MonitoredURLForm

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


def _do_check(monitored_url):
    """Realiza la verificación HTTP de una URL y actualiza el objeto (sin guardar)."""
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
        return True, response.status_code
    except http_requests.exceptions.RequestException as exc:
        monitored_url.status = MonitoredURL.STATUS_INACTIVE
        monitored_url.status_code = None
        monitored_url.response_time = None
        return False, str(type(exc).__name__)


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
