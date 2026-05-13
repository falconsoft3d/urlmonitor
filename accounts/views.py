from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .forms import RegisterForm, ProfileDataForm, AvatarForm, StyledPasswordChangeForm, UserEditForm
from .models import UserProfile


def staff_required(user):
    return user.is_active and user.is_staff

INPUT_CLASSES = (
    'w-full border border-gray-300 rounded-lg px-4 py-2.5 text-gray-900 '
    'focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent '
    'transition placeholder-gray-400'
)


def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    from monitor.models import SiteConfig
    if not SiteConfig.get().registration_enabled:
        return render(request, 'accounts/register.html', {'registration_closed': True})

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


@login_required
@user_passes_test(staff_required)
def user_list_view(request):
    users = User.objects.all().order_by('-date_joined')
    return render(request, 'accounts/user_list.html', {'users': users})


@login_required
@user_passes_test(staff_required)
def user_form_view(request, role):
    """
    Vista reutilizable de formulario.
    role = 'admin' → crea superusuario con is_staff
    role = 'usuario' → crea usuario estándar
    """
    if role not in ('admin', 'usuario'):
        return redirect('user_list')

    role_label = 'Administrador' if role == 'admin' else 'Usuario'

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            if role == 'admin':
                user.is_staff = True
                user.is_superuser = True
            user.save()
            messages.success(request, f'{role_label} «{user.username}» creado exitosamente.')
            return redirect('user_list')
    else:
        form = RegisterForm()

    return render(request, 'accounts/user_form.html', {
        'form': form,
        'role': role,
        'role_label': role_label,
    })


@login_required
@user_passes_test(staff_required)
def user_edit_view(request, pk):
    edited_user = get_object_or_404(User, pk=pk)

    if request.method == 'POST':
        form = UserEditForm(request.POST, instance=edited_user)
        if form.is_valid():
            user = form.save(commit=False)
            new_password = form.cleaned_data.get('new_password')
            if new_password:
                user.set_password(new_password)
            user.save()
            messages.success(request, f'Usuario «{user.username}» actualizado exitosamente.')
            return redirect('user_list')
    else:
        form = UserEditForm(instance=edited_user)

    return render(request, 'accounts/user_edit.html', {
        'form': form,
        'edited_user': edited_user,
    })


@login_required
def profile_view(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    tab = request.GET.get('tab', 'datos')

    data_form = ProfileDataForm(instance=request.user)
    password_form = StyledPasswordChangeForm(user=request.user)
    avatar_form = AvatarForm(instance=profile)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'datos':
            data_form = ProfileDataForm(request.POST, instance=request.user)
            if data_form.is_valid():
                data_form.save()
                messages.success(request, 'Datos actualizados correctamente.')
                return redirect(f'{request.path}?tab=datos')
            tab = 'datos'

        elif action == 'password':
            password_form = StyledPasswordChangeForm(user=request.user, data=request.POST)
            if password_form.is_valid():
                password_form.save()
                update_session_auth_hash(request, password_form.user)
                messages.success(request, 'Contraseña actualizada correctamente.')
                return redirect(f'{request.path}?tab=password')
            tab = 'password'

        elif action == 'avatar':
            avatar_form = AvatarForm(request.POST, request.FILES, instance=profile)
            if avatar_form.is_valid():
                avatar_form.save()
                messages.success(request, 'Imagen de perfil actualizada.')
                return redirect(f'{request.path}?tab=avatar')
            tab = 'avatar'

    return render(request, 'accounts/profile.html', {
        'data_form': data_form,
        'password_form': password_form,
        'avatar_form': avatar_form,
        'profile': profile,
        'tab': tab,
    })


@login_required
@require_POST
def toggle_dark_mode(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    profile.dark_mode = not profile.dark_mode
    profile.save(update_fields=['dark_mode'])
    return JsonResponse({'dark_mode': profile.dark_mode})
