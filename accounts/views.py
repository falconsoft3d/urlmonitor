from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from .forms import RegisterForm

INPUT_CLASSES = (
    'w-full border border-gray-300 rounded-lg px-4 py-2.5 text-gray-900 '
    'focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent '
    'transition placeholder-gray-400'
)


def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'¡Bienvenido, {user.username}! Tu cuenta ha sido creada exitosamente.')
            return redirect('dashboard')
    else:
        form = RegisterForm()

    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    form = AuthenticationForm(request)
    form.fields['username'].widget.attrs.update({
        'class': INPUT_CLASSES,
        'placeholder': 'tunombredeusuario',
    })
    form.fields['password'].widget.attrs.update({
        'class': INPUT_CLASSES,
        'placeholder': '••••••••',
    })

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        form.fields['username'].widget.attrs.update({'class': INPUT_CLASSES, 'placeholder': 'tunombredeusuario'})
        form.fields['password'].widget.attrs.update({'class': INPUT_CLASSES, 'placeholder': '••••••••'})

        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'¡Bienvenido de vuelta, {username}!')
                next_url = request.GET.get('next', 'dashboard')
                # Validar que next sea una ruta interna segura
                if not next_url.startswith('/') and not next_url.startswith('http'):
                    return redirect(next_url)
                return redirect(next_url if next_url.startswith('/') else 'dashboard')
        else:
            messages.error(request, 'Usuario o contraseña incorrectos.')

    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    if request.method == 'POST':
        logout(request)
        messages.info(request, 'Has cerrado sesión exitosamente.')
    return redirect('home')
